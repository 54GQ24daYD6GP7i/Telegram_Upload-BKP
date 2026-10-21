
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/brand/upload-telegram-logo-dark.svg">
  <img src="docs/brand/upload-telegram-logo-dark.svg" alt="upload-telegram" width="420">
</picture>

**Automação Profissional de Upload e Backup Estruturado para o Telegram.**

**O script definitivo para enviar cursos, treinamentos e arquivos gigantes para canais do Telegram.**
**Motor Anti-Spam inteligente, fatiamento automático de vídeos e índice estruturado. Pare de lutar contra os limites do Telegram.**

[**⚡ Como Usar**](#-como-começar) · [**✨ Diferenciais**](#-o-que-torna-este-script-diferente) · [**⏸️ Comandos**](#%EF%B8%8F-controles-e-comandos) · [**📁 Arquivos**](#-arquivos-de-controle)

> ### 🚀 Execute sem dor de cabeça
>
> Este script foi desenhado para ser **plug and play**. Você não precisa instalar dependências manualmente no terminal nem saber programar.
>
> Basta ter o Python instalado, rodar o script e **ele fará as perguntas necessárias**, instalará as bibliotecas que faltam e iniciará o upload da sua pasta direto para o Telegram, gerando um índice perfeito automaticamente.

## ⚡ Como Começar

### 1. Requisitos Básicos

Você só precisa ter o [Python](https://www.python.org/downloads/) instalado no seu computador (versão 3.8 ou superior). Certifique-se de marcar a opção *"Add Python to PATH"* durante a instalação.

### 2. Execute o Script

Abra o **Terminal** (Mac/Linux) ou **PowerShell** (Windows) na pasta onde você salvou o script e digite:

```
python upload_telegram.py

```

### O que você precisa ter em mãos na primeira execução:

| Item | Onde conseguir | 
| ----- | ----- | 
| **API ID e HASH** | Acesse [my.telegram.org](https://my.telegram.org/), faça login, vá em *API development tools* e copie os códigos. | 
| **Canal de Destino** | O `@username` público ou o ID numérico (ex: `-100123...`) do canal onde os arquivos serão salvos. | 
| **Bot Token (Opção 1)** | Crie um bot no [@BotFather](https://t.me/botfather) (Limite de 2GB por arquivo). | 
| **Conta Premium (Opção 2)** | Seu número de telefone (se quiser usar sua conta pessoal para enviar arquivos de até 4GB). | 

> 💡 **Nota Importante:** Lembre-se de adicionar o seu Bot como **Administrador** no canal de destino para que ele tenha permissão para enviar os arquivos e mensagens.

## ✨ O que torna este script diferente

Não é apenas um bot de envio. É uma ferramenta de engenharia de dados construída para lidar com as instabilidades da rede e os bloqueios da API do Telegram.

* 🛡️ **Motor Anti-Spam Inteligente:** Previne o temido `FloodWaitError`. O script usa *Jitter* (delay aleatório entre envios) e *Batching* (pausas longas de arrefecimento após X arquivos). O script analisa o peso do seu projeto e recomenda a melhor configuração.

* ✂️ **Fatiamento Automático (FFmpeg):** Tentando enviar um vídeo de 3.5GB usando um bot (limite 2GB)? O script detecta, baixa o FFmpeg silenciosamente, fatia o vídeo sem perda de qualidade e envia as partes organizadas, excluindo os temporários em seguida.

* 🌳 **Geração Dinâmica de Índice:** Ele lê a sua pasta raiz e gera uma mensagem de índice perfeita (com suporte a *Natural Sorting*, onde "Aula 2" vem antes de "Aula 10"), agrupando arquivos por hashtags únicas (`#F001`).

* ⏸️ **Checkpoints e Retomada:** A internet caiu? Você fechou o terminal? Não tem problema. O script salva o progresso em tempo real. Ao rodar novamente, ele pula o que já foi enviado.

* 🗂️ **Filtro de Extensões:** Permite ao usuário escolher exatamente quais formatos de arquivo deseja subir (ex: apenas `.mp4` e `.pdf`), ignorando arquivos brutos de edição.

## ⏸️ Controles e Comandos

O script foi desenhado com interações de terminal de alto nível. Durante o upload, você pode usar o atalho **`Ctrl + C`**:

* **Pressione 1x (Pausa Segura):** O script não quebra o arquivo atual. Ele espera o upload terminar, salva o progresso e exibe um menu perguntando se você deseja `[s] Retomar` ou `[n] Encerrar o script`.

* **Pressione novamente (Cancelar Pausa):** Desiste da pausa solicitada e continua o upload normalmente.

* **Pressione 3x rápidas (Saída Bruta 💀):** Se precisar parar tudo instantaneamente (emergência), o script corta a conexão imediatamente.

## 📁 Arquivos de Controle

Para manter a organização sem poluir seu computador, o script gera três arquivos na mesma pasta de execução:

| Arquivo | Função | 
| ----- | ----- | 
| `conf.md` | Armazena suas credenciais globais (API, Hash, Token). Não compartilhe este arquivo. | 
| `rel.md` | **O "Save Game" do projeto.** Guarda a configuração de delay, extensões escolhidas e a lista linha por linha de todos os arquivos já enviados com sucesso. | 
| `indice_gerado.txt` | Um backup local do índice estruturado que foi enviado para o Telegram. | 

## 🧱 Stack / Ferramentas Utilizadas

| Camada | Tecnologia | Função | 
| ----- | ----- | ----- | 
| **Core API** | `Telethon` (MTProto) | Permite envios superiores a 50MB (limite da API HTTP) usando chunks eficientes. | 
| **Interface** | `tqdm` | Renderiza as barras de progresso verde (Total) e azul (Upload individual) no terminal. | 
| **Metadados** | `tinytag` | Lê a duração de áudios e vídeos rapidamente para cálculo de horas totais do curso. | 
| **Mídia** | `imageio-ffmpeg` | Faz o download silencioso do motor FFmpeg para operações de corte dinâmico. | 

## 🤝 Suporte

Este é um projeto voltado para produtividade pessoal e *self-host*.

**Aviso de Privacidade:** Este script foi desenvolvido para operar localmente. As suas credenciais do Telegram e arquivos locais não são enviados para nenhum servidor externo. 

**Criado para simplificar a vida de produtores de conteúdo, arquivistas e professores.**