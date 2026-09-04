from langgraph.graph import START , END , StateGraph
from typing import TypedDict , Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage , HumanMessage
from langgraph.graph.message import add_messages
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import sqlite3

load_dotenv()
class graph_state(TypedDict):

    messages: Annotated[list[BaseMessage] , add_messages]

model = ChatGroq(
     model="openai/gpt-oss-20b",
    temperature=0.7
)

conn =sqlite3.connect(database="chatbot.db" , check_same_thread =False)


checkpointer = SqliteSaver(conn=conn)




#--------------------------------- Custom Table functions----------------------------------------------------------
conn.execute("""
    CREATE TABLE IF NOT EXISTS threads (
        thread_id TEXT PRIMARY KEY,
        title TEXT
    )
""")


conn.commit()

def save_threads(thread_id , title):
    data = get_threads_data()
    if str(thread_id) in [item['thread_id'] for item in data]:
        return 
    conn.execute(
        """INSERT INTO  threads(thread_id, title) VALUES(? ,?)""",
        (str(thread_id) , title)
        )
    conn.commit()




def get_threads_data():
    cursor = conn.execute("""
SELECT thread_id , title FROM threads
""")
    return [
        {
            "thread_id":row[0],
            "title":row[1]
        }
        for row in cursor.fetchall()
    ]

#0---------------------------------------------------------------------------------------------------------
# def threads_data():
#     temp_list = set()
#     for check in  checkpointer.list(None):
#         temp_list.add(check.config['configurable']['thread_id'])
#     return (list(temp_list))




graph = StateGraph(graph_state)

def chat_node(state:graph_state):

    # extract the message
    message = state['messages']

    # invoke the llm 
    res = model.invoke(message)

    # return the result 
    return {'messages' : [res]}

# adding the nodes 
graph.add_node("chat_node" , chat_node)

# adding the edges

graph.add_edge(START , 'chat_node')
graph.add_edge("chat_node" , END)

chatbot = graph.compile(checkpointer=checkpointer)

# chatbot.invoke({'messages':"hii how are you "} ,config={'configurable':{"thread_id":"#4bf28544-b396-44ae-be8b-9e715b96a426"}})

# #4bf28544-b396-44ae-be8b-9e715b96a426
# res = (chatbot.get_state({'configurable':{"thread_id":"#4bf28544-b396-44ae-be8b-9e715b96a426"}}))
# msg = (res.values['messages'])
# for m in msg:
#     if isinstance(m , HumanMessage):
#         print("True",m.content)
#     else:
#         print("false",m.content)


