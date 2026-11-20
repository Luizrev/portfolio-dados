# Portfolio de Análises de Dados

Este repositório reúne relatórios e análises exploratórias construídos com **Python**, **pandas**, **Power BI** e **Streamlit**, cobrindo vendas, leads, quebras e comportamento de jogadores de Valorant.

## 📂 O que tem dentro

| Pasta | Conteúdo | Ferramenta principal |
|-------|----------|---------------------|
| `Relatorio_de_vendas` | Análise de vendas: faturamento, custo, lucro, margem e devoluções. Inclui dashboard estático e modelo Power BI. | Power BI, Excel |
| `Relatorio_de_leads` | Análise de leads: volume, origem e conversão. Inclui relatório Power BI (`.pbit`). | Power BI |
| `Relatorio_de_quebras` | Análise de quebras/cancelamentos: motivos e padrões, com 3 telas de dashboard. | Power BI |
| `Relatorio_valorant` | Análise de estatísticas do Valorant: scraping de dados, pipeline ETL com notebooks, modelo relacional (Star Schema), KPIs em DAX e app Streamlit. | Python, Power BI, Streamlit, PostgreSQL |

## 🚀 Como usar

### Relatórios Power BI
Cada pasta de relatório contém um arquivo `.pbit` (template do Power BI). Para abrir:
1. Instale o [Power BI Desktop](https://powerbi.microsoft.com/desktop/) (gratuito).
2. Abra o arquivo `.pbit` da pasta desejada.
3. Carregue os dados quando solicitado.

### Análise do Valorant (Python + Streamlit)
1. Clone este repositório.
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Explore os notebooks em `Relatorio_valorant/Dados/` para ver o ETL e scraping.
4. Rode o app Streamlit:
   ```bash
   streamlit run Relatorio_valorant/src/app.py
   ```

## 🛠️ Tecnologias

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2C2D72?style=for-the-badge&logo=pandas&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-025E8C?style=for-the-badge&logo=MicrosoftSQLServer&logoColor=white)
![Power BI](https://img.shields.io/badge/PowerBI-F2C811?style=for-the-badge&logo=Power%20BI&logoColor=black)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Git](https://img.shields.io/badge/GIT-E44C30?style=for-the-badge&logo=git&logoColor=white)

## 📄 Licença

MIT
