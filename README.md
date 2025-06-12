# Vision-Azure: Processamento de Mídia Serverless na Nuvem

Este projeto é uma prova de conceito de um sistema de processamento de arquivos sob demanda, implementado de forma nativa na nuvem da Microsoft Azure. [cite_start]A arquitetura cumpre os requisitos do projeto original [cite: 1][cite_start], utilizando as seguintes tecnologias permitidas: **Azure Functions + Blob Storage**.

## Arquitetura e Serviços Utilizados

- **Azure App Service**: Hospeda o painel de controle desenvolvido em Flask, provendo uma interface web pública.
- **Azure Blob Storage**: Armazena os arquivos de entrada e saída em contêineres separados (`input-files`, `output-files`).
- **Azure Functions**: Uma função Python serverless que é acionada automaticamente por um **Blob Trigger** quando um novo arquivo é enviado para o contêiner de entrada.
- **Azure Table Storage**: Um banco de dados NoSQL utilizado para armazenar de forma persistente e escalável as estatísticas de uso das operações.
- **Application Insights**: Coleta logs, métricas e telemetria tanto da aplicação web quanto da função serverless para monitoramento centralizado.
- **Bicep (Infraestrutura como Código)**: Um arquivo declarativo (`main.bicep`) é usado para provisionar e gerenciar todos os recursos na Azure de forma automatizada e consistente.

## Funcionalidades Implementadas

[cite_start]O painel de controle web permite ao usuário executar as seguintes operações:
- Converter imagens para Preto e Branco.
- Alterar o formato de imagens (para JPEG ou PNG).
- Extrair um frame de um vídeo em um segundo específico.
- Visualizar logs e estatísticas de uso em tempo real.

## Guia de Instalação e Deploy

### Pré-requisitos
- Uma conta ativa na [Azure](https://azure.microsoft.com/free/) (a Conta Gratuita é recomendada).
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) instalado.
- [Azure Functions Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local) instalado.
- Python 3.9+.

### Passo a Passo

1.  **Login na Azure**: Abra seu terminal e autentique-se:
    ```bash
    az login
    ```

2.  **Provisionar a Infraestrutura**:
    * Crie um grupo de recursos: `az group create --name vision-azure-rg --location "Brazil South"`
    * Faça o deploy dos recursos usando o arquivo Bicep:
      ```bash
      az deployment group create --resource-group vision-azure-rg --template-file infra/main.bicep
      ```
    * Após o deploy, vá ao Portal da Azure, encontre a "Conta de Armazenamento" (Storage Account) que foi criada, vá em "Chaves de acesso" e copie a "Cadeia de conexão".

3.  **Configurar o Ambiente Local**:
    * **Frontend**: Crie o arquivo `frontend/.env` a partir do `frontend/.env.example` e cole a sua cadeia de conexão nele.
    * **Function App**: No arquivo `function_app/local.settings.json`, substitua o valor de `AzureWebJobsStorage` pela sua cadeia de conexão.

4.  **Fazer o Deploy das Aplicações**:
    * **Function App**: Navegue até a pasta `function_app/` e publique a função (substitua `NOME_DA_SUA_FUNCTION_APP` pelo nome criado pelo Bicep):
      ```bash
      func azure functionapp publish NOME_DA_SUA_FUNCTION_APP
      ```
    * **Web App**: Navegue até a pasta `frontend/` e publique a aplicação Flask (substitua `NOME_DO_SEU_WEB_APP` pelo nome criado pelo Bicep):
      ```bash
      az webapp up --name NOME_DO_SEU_WEB_APP --resource-group vision-azure-rg --sku F1
      ```

5.  **Configurar a Aplicação em Produção**:
    * No Portal da Azure, vá para o seu App Service (`webapp`). Em "Configurações" > "Configuração", adicione uma nova configuração de aplicativo chamada `AZURE_STORAGE_CONNECTION_STRING` e cole a sua cadeia de conexão. Salve as alterações.

6.  **Testar**: Acesse a URL do seu App Service para usar a aplicação.