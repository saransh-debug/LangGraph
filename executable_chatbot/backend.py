from langgraph.graph import START , END , StateGraph
from typing import TypedDict , Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage , HumanMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()
class graph_state(TypedDict):

    messages: Annotated[list[BaseMessage] , add_messages]

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")


checkpointer = MemorySaver()

graph = StateGraph(graph_state)

def chat_node(state:graph_state):

    # extract the message
    message = state['messages']

    # invoke the llm 
    res = model.invoke(message)

    # return the result 
    return {'messages' : [res.content]}

# adding the nodes 
graph.add_node("chat_node" , chat_node)

# adding the edges

graph.add_edge(START , 'chat_node')
graph.add_edge("chat_node" , END)

chatbot = graph.compile(checkpointer=checkpointer)




