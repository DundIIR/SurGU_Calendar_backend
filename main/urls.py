from django.urls import path
from .views import *


urlpatterns = [
    path('api/upload-files/', UploadAndProcessScheduleAPIView.as_view(), name='file-upload'),
    path('api/files/', FileListAPIView.as_view(), name='file-list'),
    path('api/update-role/', UpdateUserRoleAPIView.as_view(), name='update-role'),
    path('api/users/', UserListAPIView.as_view(), name='user-list'),
    path('api/validate-token/V2/', ProtectedDataAPIView.as_view(), name='validate-token'),
    path('api/check/', SearchCheck.as_view(), name='group_or_professor_check'),
    path('api/group-list/', GroupList.as_view(), name='group-list'),
    path('api/professors-list/', ProfessorsList.as_view(), name='professors-list'),
    path('api/file-schedule/', ScheduleFileView.as_view(), name='file-schedule'),
    path('api/schedule/', ListLessonsAPI.as_view(), name='schedule-list'),
    path('api/', LessonAPIList.as_view(), name='index_api'),
    path('', index, name='index'),
]


