"""blogproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

import blog.views
import comments.views
from blog.feeds import AllPostsRssFeed

router = routers.DefaultRouter()
# TODO 注册一个新的视图  参数：URL前缀、视图集、视图集生成的视图函数前缀，如果不指定就是model名称的小写（这个视图函数的名称就是 basename+action  post-list）
router.register(r"posts", blog.views.PostViewSet, basename="post")
router.register(r"categories", blog.views.CategoryViewSet, basename="category")
router.register(r"tags", blog.views.TagViewSet, basename="tag")
router.register(r"comments", comments.views.CommentViewSet, basename="comment")
router.register(r"search", blog.views.PostSearchView, basename="search")
# 仅用于 API 版本管理测试
router.register(
    r"api-version", blog.views.ApiVersionTestViewSet, basename="api-version"
)

# TODO 生成一个接口文档视图，然后我们将这个视图函数映射到了 4 个 URL
schema_view = get_schema_view(
    openapi.Info(
        title="HelloDjango REST framework tutorial API",
        default_version="v1",
        description="HelloDjango REST framework tutorial AP",
        terms_of_service="",
        contact=openapi.Contact(email="zmrenwu@163.com"),
        license=openapi.License(name="GPLv3 License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("search/", include("haystack.urls")),
    path("", include("blog.urls")),
    path("", include("comments.urls")),
    # 记得在顶部引入 AllPostsRssFeed
    path("all/rss/", AllPostsRssFeed(), name="rss"),

    # TODO api版本管理  NamespaceVersioning(namespace)  表示包含的 URL 模式均属于 v1 这个命名空间
    #  所有请求对象 request 就会多出一个属性 version，其值为用户请求的版本号（如果没有指定，就为默认的 DEFAULT_VERSION 的值）。
    #  因此，我们可以在请求中针对不同版本的请求执行不同的代码逻辑。
    path("api/v1/", include((router.urls, "api"), namespace="v1")),
    path("api/v2/", include((router.urls, "api"), namespace="v2")),
    path("api/auth/", include("rest_framework.urls", namespace="rest_framework")),
    # 文档
    re_path(
        r"swagger(?P<format>\.json|\.yaml)",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
