from celery.result import AsyncResult
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def get_ai_task_result(request, task_id):

    task = AsyncResult(task_id)

    result = None

    if task.ready():

        if task.successful():
            result = task.result
        else:
            result = str(task.result)

    return Response({
        "status": task.status,
        "result": result
    })