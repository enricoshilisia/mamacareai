import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from .models import Conversation, Message
from .services import stream_ai_reply


@login_required
def chat_home(request):
    mother   = request.user
    children = mother.children.filter(is_active=True)

    if children.count() == 1:
        child = children.first()
        conv  = _get_or_create_conversation(mother, child)
        return redirect("chat:chat_room", conv_id=conv.id)

    if children.count() == 0:
        conv = _get_or_create_conversation(mother, child=None)
        return redirect("chat:chat_room", conv_id=conv.id)

    return render(request, "chat/pick_child.html", {"children": children})


@login_required
def start_with_child(request, child_pk):
    from mothers.models import Child
    child = get_object_or_404(Child, pk=child_pk, mother=request.user, is_active=True)
    conv  = _get_or_create_conversation(request.user, child)
    return redirect("chat:chat_room", conv_id=conv.id)


def _get_or_create_conversation(mother, child):
    qs = Conversation.objects.filter(mother=mother, child=child).order_by("-updated_at")
    if qs.exists():
        return qs.first()
    return Conversation.objects.create(mother=mother, child=child)


@login_required
def chat_room(request, conv_id):
    conv     = get_object_or_404(Conversation, id=conv_id, mother=request.user)
    messages = conv.messages.order_by("created_at")

    # Serialize messages as a plain Python list — json_script will handle encoding
    messages_json = [
        {
            "role":    m.role,
            "content": m.content,
            "time":    m.created_at.strftime("%H:%M"),
        }
        for m in messages
    ]

    all_conversations = Conversation.objects.filter(
        mother=request.user
    ).order_by("-updated_at")[:30]

    return render(request, "chat/chat.html", {
        "conversation":      conv,
        "messages":          messages,
        "messages_json":     messages_json,
        "child":             conv.child,
        "all_conversations": all_conversations,
    })


@login_required
@require_POST
def stream_reply(request, conv_id):
    conv = get_object_or_404(Conversation, id=conv_id, mother=request.user)

    try:
        body      = json.loads(request.body)
        user_text = body.get("message", "").strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid request"}, status=400)

    if not user_text:
        return JsonResponse({"error": "Empty message"}, status=400)

    def event_stream():
        for chunk in stream_ai_reply(conv, user_text):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"]     = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
def conversation_list(request):
    conversations = Conversation.objects.filter(mother=request.user).order_by("-updated_at")
    return render(request, "chat/conversation_list.html", {"conversations": conversations})


@login_required
def new_conversation(request, conv_id):
    old_conv = get_object_or_404(Conversation, id=conv_id, mother=request.user)
    new_conv = Conversation.objects.create(mother=request.user, child=old_conv.child)
    return redirect("chat:chat_room", conv_id=new_conv.id)