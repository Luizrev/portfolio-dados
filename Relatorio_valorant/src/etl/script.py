import requests
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine, text
import logging
import unicodedata
import time
from dotenv import load_dotenv
import os
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

urls_to_process = [
    "https://www.vlr.gg/event/stats/2860/vct-2026-americas-stage-1",
    "https://www.vlr.gg/event/stats/2775/vct-2026-pacific-stage-1",
    "https://www.vlr.gg/event/stats/2863/vct-2026-emea-stage-1"
]

def extract_data(url: str) -> pd.DataFrame:
  """
  Extrai a tabela de estatísticas do VLR.gg e a retorna como um DataFrame bruto.
  """
  logging.info(f"Iniciando a extração de dados da URL: {url}")
  headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
  }

  try:
      response = requests.get(url, headers=headers)
      response.raise_for_status()
  except requests.exceptions.RequestException as e:
      logging.error(f"Erro ao acessar a URL: {e}")
      return None

  soup = BeautifulSoup(response.content, 'html.parser')
  stats_table = soup.find('table', class_='wf-table mod-stats mod-scroll')

  if not stats_table:
      logging.warning("Nenhuma tabela de estatísticas encontrada na página.")
      return None

  table_headers = [header.get_text(strip=True) for header in stats_table.find_all('th')]
  table_headers.pop(0)
  table_headers.insert(0, 'Player')
  table_headers.insert(1, 'Team')

  rows = []
  for row in stats_table.find('tbody').find_all('tr'):
      player_cell = row.find('td', class_='mod-player')
      player_name_div = player_cell.find('div', class_='text-of')
      player_team_div = player_cell.find('div', class_='stats-player-country')

      player = player_name_div.get_text(strip=True) if player_name_div else ''
      team = player_team_div.get_text(strip=True) if player_team_div else ''

      row_data = [player, team]
      other_cells = row.find_all('td')[1:]
      for cell in other_cells:
          span_val = cell.find('span', class_='stats-sq')
          row_data.append(span_val.get_text(strip=True) if span_val else cell.get_text(strip=True))
      rows.append(row_data)

  logging.info(f"Extração concluída. {len(rows)} linhas encontradas.")
  return pd.DataFrame(rows, columns=table_headers)

def transform_data_pre_sql(df: pd.DataFrame, region: str, year: int, tournament_name: str) -> pd.DataFrame:
    if df is None:
        return None

    logging.info(f"Transformando dados de {tournament_name} ({year})...")
    df_transformed = df.copy()

    df_transformed = df_transformed.drop(columns=['Agents'], errors='ignore')
    # Limpar a coluna KAST
    if 'KAST' in df_transformed.columns:
        df_transformed['KAST'] = df_transformed['KAST'].str.replace('%', '', regex=False)

    # Colunas para converter para tipo numérico
    cols_to_convert = ['R', 'ACS', 'K:D', 'ADR', 'KPR', 'APR', 'FKPR', 'FDPR', 'K', 'D', 'A', 'FK', 'FD', '+/-', 'KAST', 'KMax', 'Rnd', 'R2.0']

    for col in cols_to_convert:
        if col in df_transformed.columns:
            df_transformed[col] = pd.to_numeric(df_transformed[col], errors='coerce')

    # Converte KAST para decimal após garantir que é numérico
    if 'KAST' in df_transformed.columns:
        df_transformed['KAST'] /= 100.0

    if 'HS%' in df_transformed.columns:
            df_transformed['HS%'] = df_transformed['HS%'].str.replace('%', '').astype(float) / 100.0

    if 'CL%' in df_transformed.columns:
            df_transformed.loc[df_transformed['CL%'] == '', 'CL%'] = '0%'
            df_transformed['CL%'] = df_transformed['CL%'].str.replace('%', '').astype(float) / 100.0

    if 'CL' in df_transformed.columns:
            df_transformed.loc[df_transformed['CL'] == '', 'CL'] = '0/0'

    if 'R2.0' in df_transformed.columns:
            df_transformed.loc[df_transformed['R2.0'] == '', 'R2.0'] = 0

    # --- Nova Lógica de Metadados ---
    df_transformed['region'] = region
    df_transformed['year'] = year
    df_transformed['tournament_id'] = tournament_name
    
    # Criando a Chave Primária para Governança
    # Ex: "aspas_leviatan_vctamericasstage2_2025"
    df_transformed['unique_id'] = (
        df_transformed['Player'].str.lower().str.replace(' ', '') + "_" + 
        df_transformed['Team'].str.lower().str.replace(' ', '') + "_" + 
        tournament_name.lower().replace(' ', '') + "_" + 
        str(year)
    )
    
    return df_transformed

def sanitize_dataframe(df):
    """
    Limpa strings e remove acentos de colunas críticas para evitar erros de encoding.
    """
    df_clean = df.copy()
    
    # Função interna para remover acentos
    def remove_accents(input_str):
        if not isinstance(input_str, str): return input_str
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    # Aplicar limpeza em todas as colunas de texto
    for col in df_clean.select_dtypes(include=['object']).columns:
        df_clean[col] = df_clean[col].astype(str).apply(remove_accents)
        # Remove caracteres residuais que o banco possa rejeitar
        df_clean[col] = df_clean[col].str.replace(r'[^\x00-\x7F]+', '', regex=True)
    
    return df_clean

def load_to_postgres(df):
    # 1. Limpeza rigorosa antes de enviar
    df = sanitize_dataframe(df)

    load_dotenv()

    USER = os.getenv("user")
    PASSWORD = os.getenv("password")
    HOST = os.getenv("host")
    PORT = os.getenv("port")
    DBNAME = os.getenv("dbname")
    
    connection_url = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
    
    engine = create_engine(connection_url, connect_args={'client_encoding': 'utf8'})

    cols_order = [
        'unique_id', 'Player', 'Team', 'region', 'year', 'tournament_id', 
        'Rnd', 'R2.0', 'ACS', 'K:D', 'KAST', 'ADR', 'KPR', 'APR', 
        'FKPR', 'FDPR', 'HS%', 'CL%', 'CL', 'KMax', 'K', 'D', 'A', 'FK', 'FD'
    ]

    exclude_from_update = ['unique_id', 'Player', 'Team', 
                           'region', 'year', 'tournament_id']
    
    cols_to_update = [c for c in cols_order 
                      if c not in exclude_from_update]
    
    df = df[cols_order]

    try:
        df.to_sql('temp_vlr_stats', engine, if_exists='replace', index=False)
        
        columns_str = ', '.join([f'"{c}"' for c in cols_order])

        update_str = ', '.join(f'"{c}" = EXCLUDED."{c}"'
                               for c in cols_to_update)
        
        # upsert_query = f"""
        # INSERT INTO vlr_stats_players ({columns_str})
        # SELECT {columns_str} FROM temp_vlr_stats
        # ON CONFLICT (unique_id) 
        # DO UPDATE SET 
        #     "ACS" = EXCLUDED."ACS",
        #     "K:D" = EXCLUDED."K:D",
        #     "ADR" = EXCLUDED."ADR",
        #     "K" = EXCLUDED."K",
        #     "D" = EXCLUDED."D";
        # """
        upsert_query = f"""
        INSERT INTO valorant_regional_status ({columns_str})
        SELECT {columns_str} FROM temp_vlr_stats
        ON CONFLICT (unique_id) 
        DO UPDATE SET 
            {update_str}
         """
        
        with engine.begin() as conn:
            conn.execute(text(upsert_query))
            conn.execute(text("DROP TABLE IF EXISTS temp_vlr_stats;"))
            
        print("Dados integrados com sucesso!")
        
    except Exception as e:
        logging.error("Falha na carga.")
        print(f"Erro reprimido: {repr(e)}")

for url in urls_to_process:
    try:
        # --- Lógica de Extração de Metadados ---
        slug = url.split('/')[-1] # Ex: vct-2025-americas-stage-1
        partes = slug.split('-')
        
        # vct-2025-americas-stage-1 -> partes = ['vct', '2025', 'americas', 'stage', '1']
        v_year = int(partes[1])
        v_region = partes[2]
        v_tournament = f"{partes[0]}_{partes[-2]}_{partes[-1]}" # Resultado: vct_stage_1
        # v_tournament = f"{partes[0]}_{partes[-1]}" # Resultado: vct_kickoff
        
        logging.info(f"Iniciando ETL para: {v_region.upper()} | {v_tournament} | {v_year}")

        # --- Pipeline ETL ---
        
        # 1. Extract
        raw = extract_data(url)
        
        if raw is not None:
            # 2. Transform (Passando os metadados extraídos do link)
            clean = transform_data_pre_sql(
                raw, 
                region=v_region, 
                year=v_year, 
                tournament_name=v_tournament
            )
            
            # 3. Load (Injetando no banco)
            load_to_postgres(clean)
            
            logging.info(f"Sucesso total para a região {v_region}!")
            time.sleep(5)  # Pausa entre as execuções para evitar sobrecarga
        
    except Exception as e:
        logging.error(f"Erro ao processar a URL {url}: {e}")
        continue # Pula para a próxima região se uma der erro