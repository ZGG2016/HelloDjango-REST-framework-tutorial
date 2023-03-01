from django_filters import rest_framework as drf_filters

from .models import Category, Post, Tag


class PostFilter(drf_filters.FilterSet):
    # TODO 由于年份、月份这两个字段在 Post 中没有定义，Post 记录时间的字段为 created_time，因此我们需要显示地定义查询规则
    created_year = drf_filters.NumberFilter(
        field_name="created_time", lookup_expr="year", help_text="根据文章发表年份过滤文章列表。"
    )
    created_month = drf_filters.NumberFilter(
        field_name="created_time", lookup_expr="month", help_text="根据文章发表月份过滤文章列表。"
    )
    category = drf_filters.ModelChoiceFilter(
        queryset=Category.objects.all(),
        help_text="根据分类过滤文章列表。",
    )
    tags = drf_filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        help_text="根据标签过滤文章列表。",
    )

    class Meta:
        model = Post
        fields = ["category", "tags", "created_year", "created_month"]
