from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView
from django_filters.rest_framework import DjangoFilterBackend
from drf_haystack.viewsets import HaystackViewSet
from drf_yasg import openapi
from drf_yasg.inspectors import FilterInspector
from drf_yasg.utils import swagger_auto_schema
from pure_pagination.mixins import PaginationMixin
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.serializers import DateField
from rest_framework.throttling import AnonRateThrottle
from rest_framework_extensions.cache.decorators import cache_response
from rest_framework_extensions.key_constructor.bits import ListSqlQueryKeyBit, PaginationKeyBit, RetrieveSqlQueryKeyBit
from rest_framework_extensions.key_constructor.constructors import DefaultKeyConstructor

from comments.serializers import CommentSerializer

from .filters import PostFilter
from .models import Category, Post, Tag
from .serializers import (
    CategorySerializer, PostHaystackSerializer, PostListSerializer, PostRetrieveSerializer, TagSerializer)
from .utils import UpdatedAtKeyBit


class IndexView(PaginationMixin, ListView):
    model = Post
    template_name = "blog/index.html"
    context_object_name = "post_list"
    paginate_by = 10


class CategoryView(IndexView):
    def get_queryset(self):
        cate = get_object_or_404(Category, pk=self.kwargs.get("pk"))
        return super().get_queryset().filter(category=cate)


class ArchiveView(IndexView):
    def get_queryset(self):
        year = self.kwargs.get("year")
        month = self.kwargs.get("month")
        return (
            super()
            .get_queryset()
            .filter(created_time__year=year, created_time__month=month)
        )


class TagView(IndexView):
    def get_queryset(self):
        t = get_object_or_404(Tag, pk=self.kwargs.get("pk"))
        return super().get_queryset().filter(tags=t)


# 记得在顶部导入 DetailView
class PostDetailView(DetailView):
    # 这些属性的含义和 ListView 是一样的
    model = Post
    template_name = "blog/detail.html"
    context_object_name = "post"

    def get(self, request, *args, **kwargs):
        # 覆写 get 方法的目的是因为每当文章被访问一次，就得将文章阅读量 +1
        # get 方法返回的是一个 HttpResponse 实例
        # 之所以需要先调用父类的 get 方法，是因为只有当 get 方法被调用后，
        # 才有 self.object 属性，其值为 Post 模型实例，即被访问的文章 post
        response = super().get(request, *args, **kwargs)

        # 将文章阅读量 +1
        # 注意 self.object 的值就是被访问的文章 post
        self.object.increase_views()

        # 视图必须返回一个 HttpResponse 对象
        return response


# ---------------------------------------------------------------------------
#   Django REST framework 接口
# ---------------------------------------------------------------------------


class PostUpdatedAtKeyBit(UpdatedAtKeyBit):
    key = "post_updated_at"


class CommentUpdatedAtKeyBit(UpdatedAtKeyBit):
    key = "comment_updated_at"


# TODO 这个KeyConstructor包含了生成的key的逻辑和由key取值的逻辑
class PostListKeyConstructor(DefaultKeyConstructor):
    # TODO 一个 keybit 理解为 key 生成规则中的某一项规则定义
    #  自定义缓存 key 的 KeyBit
    list_sql = ListSqlQueryKeyBit()
    pagination = PaginationKeyBit()
    updated_at = PostUpdatedAtKeyBit()


class PostObjectKeyConstructor(DefaultKeyConstructor):
    retrieve_sql = RetrieveSqlQueryKeyBit()
    updated_at = PostUpdatedAtKeyBit()


class CommentListKeyConstructor(DefaultKeyConstructor):
    list_sql = ListSqlQueryKeyBit()
    pagination = PaginationKeyBit()
    updated_at = CommentUpdatedAtKeyBit()


# TODO api_view装饰器将index视图函数转变成一个类视图，并且会给这个类视图很多属性，比如认证、权限等。不写http_method_names的话，默认是get请求
@api_view(http_method_names=['get'])
def index(request):
    post_list = Post.objects.all().order_by("-created_time")
    # TODO 构造序列化器时可以传入单个对象，序列化器会将其序列化为一个字典；
    #      也可以传入包含多个对象的可迭代类型
    #      （这里的 post_list 是一个 django 的 QuerySet），此时需要设置 many 参数为 True 序列化器会依次序列化每一项，返回一个列表。
    serializer = PostListSerializer(post_list, many=True)

    return Response(serializer.data,  status=status.HTTP_200_OK)


class IndexPostListAPIView(ListAPIView):
    # TODO 基本没有写任何逻辑代码，只是指定了类视图的几个属性值。通用类视图在背后帮我们做了全部工作，我们只要告诉它：用哪个序列化器去做，序列化哪个资源等就可以了
    serializer_class = PostListSerializer
    queryset = Post.objects.all()
    # TODO 不使用指定的全局分页类，
    #  自己指定一个 pagination_class = LimitOffsetPagination，发送 API 请求：/posts/?offset=20&limit=5，将获取文章资源列表第 20 篇后的 5 篇文章
    pagination_class = PageNumberPagination
    permission_classes = [AllowAny]


class PostViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    博客文章视图集

    list:
    返回博客文章列表

    retrieve:
    返回博客文章详情

    list_comments:
    返回博客文章下的评论列表

    list_archive_dates:
    返回博客文章归档日期列表
    """

    serializer_class = PostListSerializer
    queryset = Post.objects.all()
    permission_classes = [AllowAny]
    serializer_class_table = {
        "list": PostListSerializer,
        "retrieve": PostRetrieveSerializer,
    }
    # TODO  在DjangoFilterBackend中，使用PostFilter中定义的规则过滤queryset
    filter_backends = [DjangoFilterBackend]
    filterset_class = PostFilter

    # TODO 因为处理不同的action，根据不同的action使用不同的序列化器
    def get_serializer_class(self):
        return self.serializer_class_table.get(
            self.action, super().get_serializer_class()
        )

    """
    请求被缓存的逻辑：
        1. 请求文章列表接口
        2. 根据 PostListKeyConstructor 生成缓存 key，如果使用这个 key 读取到了缓存结果，就直接返回读取到的结果，否则从数据库查询结果，并把查询的结果写入缓存。
        3. 再次请求文章列表接口，PostListKeyConstructor 将生成同样的缓存 key，这时就可以直接从缓存中读到结果并返回了。
    """
    # TODO 启用缓存功能，timeout缓存失效时间  key_func是缓存key的生成规则
    @cache_response(timeout=5 * 60, key_func=PostListKeyConstructor())
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @cache_response(timeout=5 * 60, key_func=PostObjectKeyConstructor())
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(responses={200: "归档日期列表，时间倒序排列。例如：['2020-08', '2020-06']。"})
    # TODO 用来装饰一个视图集 中的方法，被装饰的方法会被 django-rest-framework 的路由自动注册为一个 API 接口
    #      像上面的list retrieve方法被自动注册为标准的 API 接口，不使用action装饰器
    #      还可以在 action 中设置所有 ViewSet 类所支持的类属性，例如 serializer_class、pagination_class、permission_classes 等，用于覆盖类视图中设置的属性值
    @action(
        methods=["GET"],
        detail=False,
        url_path="archive/dates",  # TODO 自动注册的接口 URL
        url_name="archive-date",   # TODO 接口名
        # filter_backends=None,
        # pagination_class=None,
    )
    def list_archive_dates(self, request, *args, **kwargs):
        # TODO 取出所有的created_time字段的日期部分，精确到月份
        dates = Post.objects.dates("created_time", "month", order="DESC")
        date_field = DateField()
        # TODO 使用to_representation序列化一个字段
        data = [date_field.to_representation(date)[:7] for date in dates]
        return Response(data=data, status=status.HTTP_200_OK)

    @cache_response(timeout=5 * 60, key_func=CommentListKeyConstructor())
    @action(
        methods=["GET"],
        detail=True,
        url_path="comments",
        url_name="comment",
        # filter_backends=None,  # 移除从 PostViewSet 自动继承的 filter_backends，这样 drf-yasg 就不会生成过滤参数
        suffix="List",  # 将这个 action 返回的结果标记为列表，否则 drf-yasg 会根据 detail=True 将结果误判为单个对象
        pagination_class=LimitOffsetPagination,
        serializer_class=CommentSerializer,
    )
    def list_comments(self, request, *args, **kwargs):
        # 根据 URL 传入的参数值（文章 id）获取到博客文章记录
        post = self.get_object()
        # 获取文章下关联的全部评论
        queryset = post.comment_set.all().order_by("-created_time")
        # 对评论列表进行分页，根据 URL 传入的参数获取指定页的评论
        page = self.paginate_queryset(queryset)
        # 序列化评论
        serializer = self.get_serializer(page, many=True)
        # 返回分页后的评论列表
        return self.get_paginated_response(serializer.data)


# TODO 从视图集生成视图函数，并绑定 URL
#     字典参数就是 as_view 的action参数，将get请求和list action绑定
# index = PostViewSet.as_view({"get": "list"})


class CategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    博客文章分类视图集

    list:
    返回博客文章分类列表
    """

    serializer_class = CategorySerializer
    # 关闭分页
    pagination_class = None

    def get_queryset(self):
        return Category.objects.all().order_by("name")


class TagViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    博客文章标签视图集

    list:
    返回博客文章标签列表
    """

    serializer_class = TagSerializer
    # 关闭分页
    pagination_class = None

    def get_queryset(self):
        return Tag.objects.all().order_by("name")


class PostSearchAnonRateThrottle(AnonRateThrottle):
    # TODO 限流 单个视图设置
    THROTTLE_RATES = {"anon": "5/min"}


class PostSearchFilterInspector(FilterInspector):
    def get_filter_parameters(self, filter_backend):
        return [
            openapi.Parameter(
                name="text",
                in_=openapi.IN_QUERY,
                required=True,
                description="搜索关键词",
                type=openapi.TYPE_STRING,
            )
        ]


# TODO 在接口文档中隐藏指定视图
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        auto_schema=None,
    ),
)
# @method_decorator(
#     name="list",
#     decorator=swagger_auto_schema(
#         operation_description="返回关键词搜索结果",
#         filter_inspectors=[PostSearchFilterInspector],
#     ),
# )
class PostSearchView(HaystackViewSet):
    """
    搜索视图集

    list:
    返回搜索结果列表
    """

    index_models = [Post]
    serializer_class = PostHaystackSerializer
    # 限流
    throttle_classes = [PostSearchAnonRateThrottle]


class ApiVersionTestViewSet(viewsets.ViewSet):  # pragma: no cover
    # TODO 在接口文档中隐藏下面的接口
    swagger_schema = None

    @action(
        methods=["GET"],
        detail=False,
        url_path="test",
        url_name="test",
    )
    def test(self, request, *args, **kwargs):
        if request.version == "v1":
            return Response(
                data={
                    "version": request.version,
                    "warning": "该接口的 v1 版本已废弃，请尽快迁移至 v2 版本",
                }
            )
        return Response(data={"version": request.version})
