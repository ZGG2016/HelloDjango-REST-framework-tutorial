from django.urls import path

from . import views
from .views import index

app_name = "blog"
urlpatterns = [
    # path("", views.index),
    # path("", views.IndexPostListAPIView.as_view()),
    path("", views.IndexView.as_view(), name="index"),
    path("posts/<int:pk>/", views.PostDetailView.as_view(), name="detail"),
    path(
        "archives/<int:year>/<int:month>/", views.ArchiveView.as_view(), name="archive"
    ),
    path("categories/<int:pk>/", views.CategoryView.as_view(), name="category"),
    path("tags/<int:pk>/", views.TagView.as_view(), name="tag"),

    # TODO 从视图集生成视图函数，并绑定 URL
    # path("api/index/", index),

]
