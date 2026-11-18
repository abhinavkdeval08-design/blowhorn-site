# {{ .Title }}

> {{ .Description }}

- Category: {{ .Parent.Title }}
{{- with .Params.duration }}
- Duration: {{ . }}
{{- end }}
- Published: {{ .Date.Format "2006-01-02" }}
{{- if and (eq .Params.videoType "youtube") .Params.youtubeId (ne .Params.youtubeId "TODO_YOUTUBE_ID") }}
- Watch (YouTube): https://www.youtube.com/watch?v={{ .Params.youtubeId }}
{{- else }}{{- with .Params.video }}
- Watch (MP4): {{ .mp4 | absURL }}
{{- end }}{{- end }}

{{ .Content }}
