"""Preserve GPTScan's string-in/string-out boundary with configurable transport."""
import os
from types import SimpleNamespace
from model_transport import send

BASE_SYSTEM_MESSAGE = (
    "You are a smart contract auditor. You will be asked questions related to code properties. "
    "You can mimic answering them in the background five times and provide me with the most frequently appearing answer. "
    "Furthermore, please strictly adhere to the output format specified in the question; there is no need to explain your answer."
)
PRICE_SCOPE = (
    " Focus only on price/oracle manipulation: attacker-influenceable reserves, "
    "balances, liquidity, spot prices, exchange rates or protocol state affecting "
    "asset valuation or financial operations. Price-related names alone do not "
    "establish vulnerability. Consider existing validation and manipulation resistance. "
    "Do not report unrelated access control, reentrancy or generic bugs."
)
tokens_sent = SimpleNamespace(value=0)
tokens_received = SimpleNamespace(value=0)
tokens_sent_gpt4 = SimpleNamespace(value=0)
tokens_received_gpt4 = SimpleNamespace(value=0)


class Chat:
    def __init__(self):
        self.currentSession = []

    def newSession(self):
        self.currentSession = []

    def sendMessages(self, message, GPT4=False):
        # GPT4 is retained for caller compatibility; never silently switch models.
        system = BASE_SYSTEM_MESSAGE
        if os.environ.get("GPTSCAN_PROFILE", "price") == "price":
            system += PRICE_SCOPE
        self.currentSession = [{"role": "system", "content": system},
                               {"role": "user", "content": message}]
        return send(self.currentSession)

    def makeYesOrNoQuestion(self, question):
        return f"{question}. Please answer in one word, yes or no."

    def makeCodeQuestion(self, question, code):
        return f'Please analyze the following code, and answer the question "{question}"\n{code}'
