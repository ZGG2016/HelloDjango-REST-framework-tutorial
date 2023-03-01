from django.contrib.auth.models import User
from drf_haystack.serializers import HaystackSerializerMixin
from rest_framework import serializers
from rest_framework.fields import CharField

from .models import Category, Post, Tag
from .utils import Highlighter


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
        ]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
        ]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            "id",
            "name",
        ]


# TODO 要根据被序列化对象属性的数据类型，选择合适的序列化字段
class PostListSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    author = UserSerializer()

    # TODO 会根据绑定的模型里的字段，自动推断fields列表里序列化字段的类型（在ModelSerializer类中定义了映射关系）
    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "created_time",
            "excerpt",
            "category",
            "author",
            "views",
        ]


class PostRetrieveSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    author = UserSerializer()
    tags = TagSerializer(many=True)
    # TODO 无法推断其值的类型,人工指定该使用何种类型的序列化字段
    toc = serializers.CharField(label="文章目录", help_text="HTML 格式，每个目录条目均由 li 标签包裹。")
    body_html = serializers.CharField(
        label="文章内容", help_text="HTML 格式，从 `body` 字段解析而来。"
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "body",
            "created_time",
            "modified_time",
            "excerpt",
            "views",
            "category",
            "author",
            "tags",
            "toc",
            "body_html",
        ]


class HighlightedCharField(CharField):
    def to_representation(self, value):
        value = super().to_representation(value)
        request = self.context["request"]
        query = request.query_params["text"]
        highlighter = Highlighter(query)
        return highlighter.highlight(value)


class PostHaystackSerializer(HaystackSerializerMixin, PostListSerializer):
    title = HighlightedCharField(
        label="标题", help_text="标题中包含的关键词已由 HTML 标签包裹，并添加了 class，前端可设置相应的样式来高亮关键。"
    )
    summary = HighlightedCharField(
        source="body",
        label="摘要",
        help_text="摘要中包含的关键词已由 HTML 标签包裹，并添加了 class，前端可设置相应的样式来高亮关键。",
    )

    class Meta(PostListSerializer.Meta):
        search_fields = ["text"]
        fields = [
            "id",
            "title",
            "summary",
            "created_time",
            "excerpt",
            "category",
            "author",
            "views",
        ]
