# Helper templates for Momento Core V5 Helm Chart

{{/*
Expand the name of the chart.
*/}}
{{- define "momento-core.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "momento-core.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "momento-core.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "momento-core.labels" -}}
helm.sh/chart: {{ include "momento-core.chart" . }}
{{ include "momento-core.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "momento-core.selectorLabels" -}}
app.kubernetes.io/name: {{ include "momento-core.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "momento-core.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "momento-core.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Backend image
*/}}
{{- define "momento-core.backend.image" -}}
{{- printf "%s:%s" .Values.image.backend.repository (default .Chart.AppVersion .Values.image.backend.tag) }}
{{- end }}

{{/*
Frontend image
*/}}
{{- define "momento-core.frontend.image" -}}
{{- printf "%s:%s" .Values.image.frontend.repository (default .Chart.AppVersion .Values.image.frontend.tag) }}
{{- end }}
