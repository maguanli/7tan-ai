# -*- coding: utf-8 -*-
import sys
sys.stdout = open(sys.stdout.fileno(), 'w', encoding='utf-8', buffering=1)

with open('D:/7tan/7tanAI/src/web/routes/api_chat.py', 'r', encoding='utf-8') as f:
    content = f.read()

if '/send/stream' in content:
    print('Stream endpoint already exists')
else:
    # Add streaming import
    old_import = 'from ...agent.agent_loop import run_agent_loop'
    new_import = 'from ...agent.agent_loop import run_agent_loop, run_agent_loop_streaming'
    content = content.replace(old_import, new_import)
    
    # Add streaming endpoint before the @router.get("/history")
    stream_endpoint = '''

@router.post("/send/stream")
async def send_message_stream(req: ChatRequest):
    """SSE 流式发送对话消息 — 逐步返回思考过程和结果"""
    session_id = req.session_id or create_session()
    save_message(session_id, "user", req.message)
    
    async def event_generator():
        loop = asyncio.get_running_loop()
        # Run streaming agent in executor, collect events via queue
        queue = asyncio.Queue()
        
        def runner():
            try:
                for event in run_agent_loop_streaming(
                    task=req.message,
                    session_id=session_id,
                    model_name=req.model,
                ):
                    # Put event into queue for the async generator to pick up
                    asyncio.run_coroutine_threadsafe(queue.put(event), loop).result()
                # Signal done
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()
            except Exception as e:
                logger.error(f"Streaming agent failed: {e}")
                asyncio.run_coroutine_threadsafe(queue.put({"type": "error", "message": str(e)}), loop).result()
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()
        
        # Start runner in thread pool
        loop.run_in_executor(_get_executor(), runner)
        
        # Track full result for saving to history
        full_result = ""
        final_data = {}
        
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=300)
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Timeout - 300s'})}\\n\\n"
                break
            
            if event is None:
                break
            
            # Track text chunks for final result
            if event.get("type") == "text_chunk":
                full_result += event.get("content", "")
            elif event.get("type") == "done":
                final_data = event
                full_result = event.get("result", full_result)
                # Save final result
                save_message(session_id, "assistant", full_result)
            
            yield f"data: {json.dumps(event, ensure_ascii=False)}\\n\\n"
        
        # Final done event if not already sent
        if final_data:
            final_data["session_id"] = session_id
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\\n\\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

'''

    # Insert before the @router.get("/history") line
    insert_pos = content.find('@router.get("/history")')
    content = content[:insert_pos] + stream_endpoint + content[insert_pos:]
    
    with open('D:/7tan/7tanAI/src/web/routes/api_chat.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Stream endpoint added successfully')
