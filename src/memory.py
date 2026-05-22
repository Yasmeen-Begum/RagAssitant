conversation_history = []

def update_memory(question, answer):
    conversation_history.append({"q": question, "a": answer})
    if len(conversation_history) > 10:
        conversation_history.pop(0)

def get_history():
    return "\n".join([f"Q: {h['q']}\nA: {h['a']}" for h in conversation_history])
