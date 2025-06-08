# 📄 Consulta de Número do Cartório via RPA (Python)

Este projeto tem como objetivo **automatizar a busca do número do cartório** disponível em um site oficial, a partir de dados de endereço informados em um arquivo `.csv`. Utilizando RPA com Python, é possível realizar **consultas em lote**, otimizando processos repetitivos e manuais.

---

## 🚀 Funcionalidades

- Leitura de arquivo `.csv` com múltiplos endereços
- Consulta automatizada via RPA (web scraping ou interação com site)
- Extração do número do cartório correspondente ao endereço informado
- Exportação dos resultados para um novo arquivo

---

## 📁 Formato do CSV de Entrada

O arquivo deve conter os seguintes campos separados por **ponto e vírgula (;)**:


> ⚠️ O campo `rua` deve conter o **nome da rua e o número do imóvel** no seguinte formato:
>  
> `Rua Exemplo, 123`

Exemplo: Av. Paulista, 1578;Bela Vista;São Paulo;SP;01310-200;Brasil

---

## 🛠 Pré-requisitos

- Python 3.8+
- Bibliotecas utilizadas:
  - `pandas`
  - `selenium`
  - `webdriver-manager`
  - (adicione outras se necessário)

Para instalar as dependências:

```bash
pip install -r requirements.txt


git clone https://github.com/seuusuario/nome-do-repositorio.git
