# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('D:/7tan/7tanAI/src/agent/agent_loop.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'def run_agent_loop_streaming' in content:
    print('Streaming version already exists')
else:
    streaming_code = '''

def run_agent_loop_streaming(
    task: str,
    session_id: str = None,
    model_name: str = None,
    max_iterations: int = 80,
):
    """
    Streaming Agent loop - yields events for frontend display
    
    Yields:
        dict events: 
            {"type": "thinking", "message": "..."}
            {"type": "text_chunk", "content": "..."}
            {"type": "tool_call", "tool_name": "...", "args": {...}}
            {"type": "tool_result", "tool_name": "...", "summary": "...", "error": bool}
            {"type": "iteration", "iteration": 1, "max_iterations": 80}
            {"type": "cost", "cost": 0.001}
            {"type": "done", "success": bool, "result": "...", "cost": 0.0, "iterations": 0}
            {"type": "error", "message": "..."}
    """
    from ..config.loader import load_config
    config = load_config()
    active_ai = _get_active_ai_config(config)

    actual_model = model_name or active_ai.get("model", "deepseek-chat")
    model = get_model(actual_model)
    ctx = ContextManager(task=task, session_id=session_id)
    system_prompt = _build_system_prompt(config)

    messages = [{"role": "system", "content": system_prompt}]

    # Load history
    if session_id:
        try:
            from ..agent.conversation import get_session_messages
            history = get_session_messages(session_id, limit=30)
            hist_tokens = 0
            kept = []
            for m in reversed(history):
                t = len(m.get("content", "")) // 2
                if hist_tokens + t > 16000:
                    break
                entry = {"role": m["role"], "content": m.get("content", "")}
                if "tool_calls" in m and m["tool_calls"]:
                    entry["tool_calls"] = m["tool_calls"]
                if "tool_call_id" in m and m["tool_call_id"]:
                    entry["tool_call_id"] = m["tool_call_id"]
                kept.insert(0, entry)
                hist_tokens += t
            messages.extend(kept)
            if kept:
                messages = _repair_messages(messages)
        except Exception as e:
            logger.warning(f"Load history failed: {e}")

    messages.append({"role": "user", "content": task})
    yield {"type": "thinking", "message": "Task loaded, starting..."}

    total_cost = 0.0
    all_logs = []
    last_calls = []

    for iteration in range(1, max_iterations + 1):
        yield {"type": "iteration", "iteration": iteration, "max_iterations": max_iterations}
        yield {"type": "thinking", "message": f"Round {iteration}/{max_iterations} reasoning..."}

        try:
            messages = _repair_messages(messages)
            response = _call_llm(
                model=model,
                messages=messages,
                tools=get_all_tools(),
                config=config,
            )
        except Exception as e:
            import traceback
            logger.error(f"LLM call failed: {e}\\n{traceback.format_exc()}")
            ctx.add_assistant_message(f"Error: {e}")
            yield {"type": "error", "message": f"LLM call failed: {e}"}
            yield {"type": "done", "success": False, "result": f"LLM call failed: {e}", "cost": total_cost, "iterations": iteration}
            return

        usage = response.usage
        if usage:
            cost = track_cost_internal(
                model=actual_model,
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
            )
            total_cost += cost
            yield {"type": "cost", "cost": cost}

        choice = response.choices[0]
        msg = choice.message
        finish_reason = choice.finish_reason or ""

        msg_dict = {"role": "assistant"}
        if msg.content:
            msg_dict["content"] = msg.content
        if msg.tool_calls:
            safe_calls = []
            for tc in msg.tool_calls:
                fn = tc.function
                safe_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": fn.name if hasattr(fn, 'name') else fn.get("name", ""),
                        "arguments": fn.arguments if hasattr(fn, 'arguments') else fn.get("arguments", ""),
                    }
                })
            msg_dict["tool_calls"] = safe_calls
        messages.append(msg_dict)

        content = msg.content or ""
        tool_calls_raw = msg.tool_calls
        all_logs.append({
            "iteration": iteration,
            "role": "assistant",
            "content": content,
            "tool_calls": [tc.model_dump() for tc in tool_calls_raw] if tool_calls_raw else None,
            "finish_reason": finish_reason,
        })

        if content:
            ctx.add_assistant_message(content)
            yield {"type": "text_chunk", "content": content}

        if finish_reason == "length":
            messages.append({"role": "user", "content": "Output truncated, please continue."})
            continue
        if finish_reason == "stop" or (not tool_calls_raw and content):
            yield {"type": "thinking", "message": "Done"}
            yield {"type": "done", "success": True, "result": content or "Done", "cost": total_cost, "iterations": iteration}
            return

        if not tool_calls_raw:
            messages.append({"role": "user", "content": "Please continue or call tools."})
            continue

        for tc in tool_calls_raw:
            try:
                func = tc.function if hasattr(tc, 'function') else tc.get("function", {})
                tool_name = func.name if hasattr(func, 'name') else func.get("name", "unknown")
                tool_args_raw = func.arguments if hasattr(func, 'arguments') else func.get("arguments", "{}")
                tool_id = tc.id if hasattr(tc, 'id') else tc.get("id", "")
                tool_args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw

                logger.info(f"Call tool: {tool_name}({_truncate_args(tool_args)})")
                yield {"type": "tool_call", "tool_name": tool_name, "args": tool_args}

                call_sig = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
                last_calls.append(call_sig)
                if len(last_calls) > 5:
                    last_calls.pop(0)
                if len(last_calls) >= 3 and len(set(last_calls[-3:])) == 1:
                    logger.warning(f"Dead loop detected: {call_sig}")
                    yield {"type": "tool_result", "tool_name": tool_name, "summary": "Dead loop detected", "error": True}
                    yield {"type": "done", "success": False,
                           "result": f"Dead loop detected - tool {tool_name} called 3 times with same args",
                           "cost": total_cost, "iterations": iteration}
                    return

                result_str = execute_tool(tool_name, tool_args)
                if len(result_str) > 100000:
                    result_str = result_str[:100000] + "\\n...(truncated)"

                summary = result_str[:200] + "..." if len(result_str) > 200 else result_str
                yield {"type": "tool_result", "tool_name": tool_name, "summary": summary, "error": False}

            except Exception as tool_err:
                import traceback
                logger.error(f"Tool failed [{tool_name}]: {tool_err}\\n{traceback.format_exc()}")
                result_str = f"Error: {tool_err}"
                yield {"type": "tool_result", "tool_name": tool_name, "summary": f"Error: {tool_err}", "error": True}

            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": result_str,
            })

    yield {"type": "thinking", "message": f"Max iterations {max_iterations} reached"}
    yield {"type": "done", "success": False,
           "result": f"Max iterations {max_iterations} reached, task incomplete",
           "cost": total_cost, "iterations": max_iterations}
'''

    with open('D:/7tan/7tanAI/src/agent/agent_loop.py', 'a', encoding='utf-8') as f:
        f.write(streaming_code)
    print('Streaming version appended successfully')
