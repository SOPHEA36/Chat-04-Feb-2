#!/usr/bin/env python3
"""
GUI Chatbot Application for RAG Car Recommendation System
Uses Gradio for a clean, user-friendly interface
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any
import gradio as gr

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.chat_assistant import (
    load_full_rows,
    build_rag_engine,
    chat_turn,
    render_answer,
)


class ChatbotApp:
    """Chatbot application with state management"""

    def __init__(self):
        print("Loading car dataset...")
        self.full_rows = load_full_rows()
        print(f"Loaded {len(self.full_rows)} car records")

        print("Initializing RAG engine...")
        self.rag = build_rag_engine(self.full_rows)
        print("RAG engine ready")

        # Configuration
        self.use_llm = True
        self.rewrite_csv = False  # Keep CSV answers strict
        self.debug = False

    def reset_state(self) -> Dict[str, Any]:
        """Create a fresh conversation state"""
        return {
            "last_model": None,
            "slots": {
                "max_budget": None,
                "min_seats": None,
                "fuel": None,
                "body_type": None
            },
            "slot_fill_active": False,
            "slot_fill_missing": [],
            "last_reco": None,
            "awaiting_model_for": None,
        }

    def process_message(
            self,
            message: str,
            history: List[Tuple[str, str]],
            state: Dict[str, Any]
    ) -> Tuple[List[Tuple[str, str]], Dict[str, Any]]:
        """
        Process user message and return updated history and state

        Args:
            message: User input text
            history: Chat history as list of (user_msg, bot_msg) tuples
            state: Conversation state dictionary

        Returns:
            Updated history and state
        """
        if not message or not message.strip():
            return history, state

        # Handle special commands
        if message.strip().lower() == "/reset":
            state = self.reset_state()
            history.append((message, "✅ Conversation reset. How can I help you?"))
            return history, state

        if message.strip().lower() == "/debug on":
            self.debug = True
            history.append((message, "✅ Debug mode enabled"))
            return history, state

        if message.strip().lower() == "/debug off":
            self.debug = False
            history.append((message, "✅ Debug mode disabled"))
            return history, state

        # Process the message through chat assistant
        try:
            result = chat_turn(
                message,
                state,
                self.full_rows,
                self.rag,
                debug=self.debug
            )

            # Render the answer
            bot_response = render_answer(
                message,
                result,
                use_llm=self.use_llm,
                rewrite_csv=self.rewrite_csv,
                debug=self.debug
            )

            # Add to history
            history.append((message, bot_response))

        except Exception as e:
            error_msg = f"❌ Error processing message: {str(e)}"
            if self.debug:
                import traceback
                error_msg += f"\n\n```\n{traceback.format_exc()}\n```"
            history.append((message, error_msg))

        return history, state


def create_interface() -> gr.Blocks:
    """Create and configure the Gradio interface"""

    app = ChatbotApp()

    with gr.Blocks(
            title="Toyota Car Assistant",
            theme=gr.themes.Soft()
    ) as interface:
        gr.Markdown(
            """
            # 🚗 Toyota Car Recommendation Assistant

            Ask me about:
            - **Price**: "What's the price of Camry?"
            - **Specs**: "Show me Corolla specs"
            - **Features**: "Does Fortuner have BSM?"
            - **Compare**: "Compare Yaris Cross vs Corolla Cross"
            - **Recommend**: "Recommend a hybrid SUV under $50,000"

            **Commands**: `/reset` - Reset conversation | `/debug on/off` - Toggle debug mode
            """
        )

        # State management
        state = gr.State(value=app.reset_state())

        # Chatbot interface
        chatbot = gr.Chatbot(
            value=[],
            height=500,
            label="Chat History",
            show_label=True,
            avatar_images=(None, "🤖"),
            bubble_full_width=False
        )

        with gr.Row():
            msg = gr.Textbox(
                placeholder="Type your question here... (e.g., 'I want a hybrid SUV under $50,000')",
                label="Your Message",
                scale=9,
                lines=1,
                max_lines=3,
                autofocus=True
            )
            send_btn = gr.Button(
                "Send",
                variant="primary",
                scale=1,
                size="lg"
            )

        with gr.Row():
            clear_btn = gr.Button("🗑️ Clear Chat", size="sm")
            reset_btn = gr.Button("🔄 Reset State", size="sm")

        gr.Markdown(
            """
            ---
            ### Tips:
            - Be specific about your requirements (budget, fuel type, body type)
            - You can ask follow-up questions about the same car
            - The assistant remembers context within the conversation
            """
        )

        # Event handlers
        def respond(message, history, conv_state):
            """Handle user message"""
            return app.process_message(message, history, conv_state)

        def clear_chat():
            """Clear chat history but keep state"""
            return [], None

        def reset_conversation(conv_state):
            """Reset both chat and state"""
            new_state = app.reset_state()
            return [], new_state, None

        # Button click events
        msg.submit(
            respond,
            inputs=[msg, chatbot, state],
            outputs=[chatbot, state]
        ).then(
            lambda: None,  # Clear input box
            None,
            msg
        )

        send_btn.click(
            respond,
            inputs=[msg, chatbot, state],
            outputs=[chatbot, state]
        ).then(
            lambda: None,  # Clear input box
            None,
            msg
        )

        clear_btn.click(
            clear_chat,
            inputs=None,
            outputs=[chatbot, msg]
        )

        reset_btn.click(
            reset_conversation,
            inputs=[state],
            outputs=[chatbot, state, msg]
        )

    return interface


def main():
    """Launch the application"""
    interface = create_interface()

    # Launch with configuration
    interface.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7860,  # Default Gradio port
        share=False,  # Set True to create public link
        show_error=True,
        show_api=False
    )


if __name__ == "__main__":
    main()