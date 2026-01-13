{{/*
Expand the name of the chart.
*/}}
{{- define "rcsb-pdb-chatbot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "rcsb-pdb-chatbot.fullname" -}}
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
{{- define "rcsb-pdb-chatbot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "rcsb-pdb-chatbot.labels" -}}
helm.sh/chart: {{ include "rcsb-pdb-chatbot.chart" . }}
{{ include "rcsb-pdb-chatbot.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "rcsb-pdb-chatbot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rcsb-pdb-chatbot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "rcsb-pdb-chatbot.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "rcsb-pdb-chatbot.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name for PVC user data
*/}}
{{- define "rcsb-pdb-chatbot.pvcUserData" -}}
{{- printf "%s-user-data" (include "rcsb-pdb-chatbot.fullname" .) }}
{{- end }}

{{/*
Create the name for PVC credentials
*/}}
{{- define "rcsb-pdb-chatbot.pvcCredentials" -}}
{{- printf "%s-credentials" (include "rcsb-pdb-chatbot.fullname" .) }}
{{- end }}

{{/*
Create the name for PVC knowledge base
*/}}
{{- define "rcsb-pdb-chatbot.pvcKnowledgeBase" -}}
{{- printf "%s-knowledge-base" (include "rcsb-pdb-chatbot.fullname" .) }}
{{- end }}

{{/*
Create the name for ConfigMap
*/}}
{{- define "rcsb-pdb-chatbot.configMapName" -}}
{{- printf "%s-config" (include "rcsb-pdb-chatbot.fullname" .) }}
{{- end }}
