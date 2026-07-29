# SLO Demo na AWS via CloudFormation

Sobe a mesma stack de observabilidade do `docker-compose.yml` da raiz do
projeto (Prometheus, Grafana, node_exporter, cAdvisor, Redis, app Flask,
OTel Collector) mais o **agente do Gremlin** para chaos engineering, rodando
em **ECS (launch type EC2)** sobre **uma unica instancia EC2**, para ligar e
desligar sob demanda em aulas de SRE.

O app Flask nao fala mais o formato de metricas do Prometheus diretamente:
ele exporta via **OTLP para um OTel Collector**, que reexporta para o
Prometheus (formato vendor-neutro — no futuro da so trocar o exporter do
Collector para apontar a qualquer outro backend de observabilidade sem
tocar no codigo da aplicacao).

Arquitetura: [architecture.excalidraw](architecture.excalidraw) (abra em
https://excalidraw.com > File > Open).

## Por que ECS com EC2 (e nao Fargate)

`node_exporter`, `cadvisor` e o agente **Gremlin** dependem de acesso ao
host (`pid: host`, socket do Docker, `/sys`, `/var/lib/docker`) — isso
**nao funciona no Fargate**, que nao expoe o host nem o socket do Docker
aos containers (o Gremlin so suporta EC2-backed ECS; para Fargate a
Gremlin recomenda o produto "Failure Flags", fora do escopo aqui). Por
isso todos os 8 containers rodam em modo `host` de rede numa unica
instancia EC2 registrada no cluster (mesmo padrao do `docker-compose.yml`
atual, so que orquestrado por ECS em vez de Compose) — o que tambem
simplifica o endereco do collector: o app fala com ele em
`localhost:4317` porque estao no mesmo host.

O Gremlin roda como **ECS Service com `SchedulingStrategy: DAEMON`** (um
agente por instancia do cluster) em vez de `REPLICA` como os outros 6 —
e o padrao recomendado pela Gremlin para o agente, e ja deixa o template
pronto para o dia em que a instancia unica virar mais de uma.

## Credenciais do Gremlin

O template exige dois parametros obrigatorios (sem default, `NoEcho`):

- `GremlinTeamID` e `GremlinTeamSecret` — pegue em
  https://app.gremlin.com/settings/teams (Team Secret fica junto do Team ID
  na mesma tela).

Sem eles o `create-stack` falha na validacao de parametros (nao sobe uma
stack com o agente incapaz de autenticar). Depois do deploy, confirme o
registro em https://app.gremlin.com/clients/ filtrando pela tag
`platform=ecs` (o output `GremlinVerifyURL` traz esse link).

## Custo

- 1x EC2 (default `t3.medium`, 4GiB) — o Gremlin sozinho reserva 1024
  CPU/1024MB (recomendacao oficial) e agora sao 8 containers no total, o
  que nao cabe com folga num `t3.micro`/`t3.small`. Use `t3.micro` apenas
  se remover o Gremlin e o OTel Collector da stack. `t3.medium` on-demand
  gira em torno de US$ 0,04/hora — para uma aula de 2h isso e centavos.
- ECS Cluster/Service/Task Definition: sem custo adicional (voce paga so a
  instancia EC2 por baixo).
- Elastic IP: gratuito enquanto associado a uma instancia em execucao.
- CloudWatch Logs: retencao de 3 dias, dentro do free tier para o volume de
  uma demo.
- Imagens vem do Docker Hub publico (sem ECR, sem custo de registry).

**Para custo zero entre aulas**: delete a stack (`delete-stack`). Como tudo
e recriado pelo template (VPC, IPs, volumes de dados), nao fica nada
provisionado pago quando a stack nao existe.

## Deploy

```bash
aws cloudformation create-stack \
  --stack-name slo-demo \
  --template-body file://slo-demo.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
      ParameterKey=AllowedCidr,ParameterValue=SEU_IP/32 \
      ParameterKey=GremlinTeamID,ParameterValue=SEU_TEAM_ID \
      ParameterKey=GremlinTeamSecret,ParameterValue=SEU_TEAM_SECRET

aws cloudformation wait stack-create-complete --stack-name slo-demo

aws cloudformation describe-stacks --stack-name slo-demo \
  --query 'Stacks[0].Outputs' --output table
```

Leva alguns minutos: a instancia precisa subir, o agente ECS se registrar
no cluster e os 8 services (7 `REPLICA` + 1 `DAEMON` do Gremlin) alocarem
suas tasks. Os `Outputs` trazem as URLs de Grafana, Prometheus, app e
cAdvisor prontas com o Elastic IP, alem do link para conferir o Gremlin.

Restrinja `AllowedCidr` ao seu IP (`curl ifconfig.me` + `/32`) antes de
demonstrar em aula publica — o default `0.0.0.0/0` e so para conveniencia
inicial.

## Derrubar

```bash
aws cloudformation delete-stack --stack-name slo-demo
aws cloudformation wait stack-delete-complete --stack-name slo-demo
```

## Acessar sem SSH

A role da instancia inclui SSM, então dá para abrir um shell sem key pair
nem porta 22 exposta:

```bash
aws ssm start-session --target $(aws cloudformation describe-stacks \
  --stack-name slo-demo --query \
  "Stacks[0].Outputs[?OutputKey=='SSMSessionCommand'].OutputValue" \
  --output text | awk '{print $NF}')
```

## Limitacoes conhecidas (demo, nao producao)

- 1 instancia, sem alta disponibilidade — de proposito, e uma demo de sala
  de aula, nao um ambiente produtivo.
- Dados (Prometheus TSDB, dashboards do Grafana, Redis) ficam em bind
  mounts no disco da instancia (`/opt/monitoring/*`) — persistem entre
  restart de container mas **somem quando a stack e deletada** (o volume
  EBS da instancia vai junto). Se quiser preservar dashboards entre aulas,
  exporte-os do Grafana antes de destruir a stack, ou provisionamos um
  volume EBS separado com `DeletionPolicy: Retain` depois.
- Memoria segue apertada mesmo no `t3.medium` (4GiB) com o Gremlin reservando
  1024MB sozinho e mais 7 containers — se o scheduler do ECS falhar em
  alocar alguma task por falta de memoria, use um `InstanceType` maior.
- O Gremlin roda com Linux capabilities elevadas (`NET_ADMIN`, `SYS_ADMIN`,
  `SYS_BOOT`, etc.) e acesso ao socket do Docker — isso e inerente a como o
  agente injeta falhas (latencia de rede, kill de processo, disk I/O). E o
  minimo exigido pela propria Gremlin para o modo ECS/EC2, nao uma escolha
  deste template.
- O app nao expoe mais `/metrics` (nao usa mais `prometheus_client`) — toda
  metrica sai via OTLP para o OTel Collector em `localhost:4317`, que
  reexporta em formato Prometheus na porta `9464`. O Prometheus do stack
  escaneia o Collector, nao o app diretamente.
