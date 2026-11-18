{{- $id := strings.TrimSpace (.Get "id" | default "") -}}
{{- $title := .Get "title" | default "Video" -}}
{{- if and $id (ne $id "TODO_YOUTUBE_ID") -}}
[Watch {{ $title }}](https://www.youtube.com/watch?v={{ $id }})
{{- else -}}
{{ $title }} (YouTube ID not set yet).
{{- end }}
