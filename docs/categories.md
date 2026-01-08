---
layout: default
title: カテゴリ
---

# カテゴリ一覧

{% assign categories = site.posts | map: "categories" | uniq | sort %}

<ul class="category-list">
{% for category in site.categories %}
  <li id="{{ category[0] | slugify }}">
    <a href="#{{ category[0] | slugify }}">
      <span>{{ category[0] }}</span>
      <span class="category-count">{{ category[1].size }}件</span>
    </a>
  </li>
{% endfor %}
</ul>

---

{% for category in site.categories %}
## {{ category[0] }}

<ul class="post-list">
{% for post in category[1] %}
  <li>
    <article class="post-preview">
      <div class="post-info">
        <h3>
          <a href="{{ post.url | relative_url }}">{{ post.title | escape }}</a>
        </h3>
        <time datetime="{{ post.date | date_to_xmlschema }}">
          {{ post.date | date: "%Y年%m月%d日" }}
        </time>
        {% if post.description %}
          <p class="post-excerpt">{{ post.description | truncate: 100 }}</p>
        {% endif %}
      </div>
    </article>
  </li>
{% endfor %}
</ul>
{% endfor %}
