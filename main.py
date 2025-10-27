import streamlit as st
import pandas as pd
from merge_logic import (
    extract_well_letter,
    merge_tables_corrected,
    add_column_headers
)
from io import BytesIO

TIME_POINTS = ["1h", "4h", "12h", "24h"]

st.set_page_config(page_title="Объединение таблиц", layout="wide")
st.title("📊 Объединение таблиц эксперимента по временным точкам")

uploaded_files = {}
all_wells = set()

for tp in TIME_POINTS:
    st.session_state.setdefault(f"exposure_time_{tp}", tp)
    st.session_state.setdefault(f"download_data_{tp}", None)

st.subheader("1. Загрузка файлов по временным точкам")
for time_point in TIME_POINTS:
    with st.expander(f"Загрузка для {time_point}", expanded=True):
        files = st.file_uploader(
            f"Загрузите 3 Excel-файла для {time_point}",
            type=["xlsx"],
            accept_multiple_files=True,
            key=f"uploader_{time_point}"
        )
        if files:
            uploaded_files[time_point] = files
            for file in files:
                try:
                    df = pd.read_excel(file, header=None)
                    well_ids = df.iloc[:, 1].dropna().unique()
                    all_wells.update([extract_well_letter(w) for w in well_ids if isinstance(w, str)])
                except Exception as e:
                    st.error(f"Ошибка при чтении файла для {time_point}: {e}")

if any(len(files) == 3 for files in uploaded_files.values()):
    st.subheader("2. Ввод параметров эксперимента")

    if "compound" not in st.session_state:
        st.session_state["compound"] = ""

    def update_compound():
        st.session_state["compound"] = st.session_state["compound_input"]

    st.text_input(
        "Compound",
        value=st.session_state["compound"],
        key="compound_input",
        on_change=update_compound
    )

    st.markdown("---")
    st.subheader("3. Ввод концентраций по группам лунок")

    well_letters = sorted(set([w for w in all_wells if isinstance(w, str) and len(w) == 1]))
    concentrations = {}
    cols = st.columns(len(well_letters))
    for i, well in enumerate(well_letters):
        with cols[i]:
            if well == "A":
                concentrations[well] = ""
                st.text_input(f"{well} (Control)", value="0 (авто)", disabled=True)
            else:
                key = f"conc_{well}"
                if key not in st.session_state:
                    st.session_state[key] = ""

                def update_conc(w=well):
                    st.session_state[w] = st.session_state[f"conc_{w}_input"]

                concentrations[well] = st.text_input(
                    f"{well}*",
                    value=st.session_state[key],
                    key=f"conc_{well}_input",
                    on_change=update_conc
                )

    st.markdown("---")
    st.subheader("4. Объединение и скачивание результатов")

    for time_point in TIME_POINTS:
        with st.container():
            st.markdown(f"**🕐 {time_point}**")

            if len(uploaded_files.get(time_point, [])) == 3:
                def update_exposure(tp=time_point):
                    st.session_state[f"exposure_time_{tp}"] = st.session_state[f"exposure_time_input_{tp}"]

                st.text_input(
                    f"Exposure time for {time_point}",
                    value=st.session_state[f"exposure_time_{time_point}"],
                    key=f"exposure_time_input_{time_point}",
                    on_change=update_exposure
                )

                if st.button(f"🔄 Объединить файлы для {time_point}", key=f"merge_{time_point}"):
                    try:
                        typed_tables = {1: None, 2: None, 3: None}

                        for f in uploaded_files[time_point]:
                            df = pd.read_excel(f, header=None)
                            n_cols = df.shape[1]

                            if n_cols >= 8 and typed_tables[2] is None:
                                typed_tables[2] = df
                            elif n_cols >= 7 and typed_tables[1] is None:
                                typed_tables[1] = df
                            elif n_cols >= 5 and typed_tables[3] is None:
                                typed_tables[3] = df
                            else:
                                st.warning(f"❓ Не удалось однозначно определить тип таблицы для файла: {f.name}")

                        if any(v is None for v in typed_tables.values()):
                            st.error("❌ Не удалось определить все 3 таблицы. Проверьте содержимое файлов.")
                        else:
                            experiment_id_label = f"Trial     {TIME_POINTS.index(time_point) + 1}"

                            result_df = merge_tables_corrected(
                                typed_tables[1], typed_tables[2], typed_tables[3],
                                st.session_state[f"exposure_time_{time_point}"],
                                st.session_state["compound"],
                                concentrations,
                                experiment_id_label
                            )

                            if result_df.empty:
                                st.error("❌ Пустой результат. Проверьте содержимое таблиц.")
                            else:
                                result_df_with_headers = add_column_headers(result_df)
                                
                                # Удаление суффикса (alt)
                                result_df_with_headers.iloc[0] = [
                                    str(col).replace(" (alt)", "").replace("(alt)", "")  # безопасно
                                    for col in result_df_with_headers.iloc[0]
                                ]

                                output = BytesIO()
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    result_df_with_headers.to_excel(writer, index=False, header=False)
                                output.seek(0)

                                st.session_state[f"download_data_{time_point}"] = output

                    except Exception as e:
                        st.error(f"Ошибка при объединении: {e}")

            if st.session_state.get(f"download_data_{time_point}"):
                st.download_button(
                    label=f"📥 Скачать Excel для {time_point}",
                    data=st.session_state[f"download_data_{time_point}"],
                    file_name=f"Statistics-{st.session_state["compound"]}-{time_point}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_btn_{time_point}"
                )
            else:
                st.info(f"Загрузите 3 файла для {time_point}, чтобы активировать объединение.")
