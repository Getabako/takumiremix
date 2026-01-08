---
layout: default
title: アーカイブ
---

# 記事アーカイブ

すべての記事を日付順に表示しています。

<div class="archive">
{% assign posts_by_year = site.posts | group_by_exp: "post", "post.date | date: '%Y'" %}
{% for year in posts_by_year %}
  <h2 class="archive-year">{{ year.name }}年</h2>
  <ul class="archive-list">
    {% for post in year.items %}
    <li class="archive-item">
      <time datetime="{{ post.date | date_to_xmlschema }}">
        {{ post.date | date: "%m月%d日" }}
      </time>
      <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
      {% if post.categories.size > 0 %}
        <span class="archive-category">{{ post.categories | first }}</span>
      {% endif %}
    </li>
    {% endfor %}
  </ul>
{% endfor %}
</div>
