import streamlit as st

from shopping_llm import (
    FORMAT_OPTIONS,
    MAX_DISH_LENGTH,
    PEOPLE_OPTIONS,
    UserFacingError,
    generate_shopping_list_sync,
)

st.set_page_config(
    page_title="Умный список покупок",
    page_icon="🥕",
    layout="centered",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #17332a;
        --muted: #5f7069;
        --surface: #f6f2e9;
        --accent: #e05f2f;
        --accent-dark: #b8421c;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 12% 8%, rgba(224, 95, 47, 0.12), transparent 27rem),
            linear-gradient(180deg, #fffdf8 0%, var(--surface) 100%);
        color: var(--ink);
    }
    header[data-testid="stHeader"] {
        display: none;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 760px;
        padding-top: 3.25rem;
        padding-bottom: 4rem;
    }
    .eyebrow {
        color: var(--accent-dark);
        font-size: 0.78rem;
        font-weight: 750;
        letter-spacing: 0.13em;
        margin-bottom: 0.65rem;
        text-transform: uppercase;
    }
    .hero-title {
        color: var(--ink);
        font-size: clamp(2.2rem, 8vw, 4.35rem);
        font-weight: 760;
        letter-spacing: -0.055em;
        line-height: 0.96;
        margin: 0 0 1rem;
        max-width: 12ch;
    }
    .hero-copy {
        color: var(--muted);
        font-size: 1.05rem;
        line-height: 1.65;
        margin-bottom: 2rem;
        max-width: 58ch;
    }
    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.84);
        border: 1px solid rgba(23, 51, 42, 0.14);
        border-radius: 22px;
        box-shadow: 0 24px 70px rgba(23, 51, 42, 0.09);
        padding: 1.25rem 1.25rem 1.4rem;
    }
    .stButton > button, [data-testid="stFormSubmitButton"] button {
        background: var(--accent) !important;
        border: 0 !important;
        border-radius: 999px;
        color: white !important;
        font-weight: 700;
        min-height: 3rem;
        transition: background 120ms ease, transform 120ms ease;
    }
    .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
        background: var(--accent-dark) !important;
        color: white !important;
        transform: translateY(-1px);
    }
    .stButton > button:focus-visible,
    [data-testid="stFormSubmitButton"] button:focus-visible {
        outline: 3px solid rgba(224, 95, 47, 0.3);
        outline-offset: 3px;
    }
    .result-label {
        color: var(--accent-dark);
        font-size: 0.78rem;
        font-weight: 750;
        letter-spacing: 0.12em;
        margin-top: 1.6rem;
        text-transform: uppercase;
    }
    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"] {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 2rem;
        }
        div[data-testid="stForm"] {
            border-radius: 17px;
            padding: 0.85rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="eyebrow">Меню без лишних догадок</p>', unsafe_allow_html=True)
st.markdown('<h1 class="hero-title">Список покупок за минуту</h1>', unsafe_allow_html=True)
st.markdown(
    """
    <p class="hero-copy">
        Напишите блюдо, укажите количество людей и получите готовый список продуктов.
        При желании добавим короткий план приготовления.
    </p>
    """,
    unsafe_allow_html=True,
)

with st.form("shopping-list-form"):
    dish = st.text_area(
        "Что хотите приготовить?",
        placeholder="Например: овощная лазанья",
        height=118,
        help=f"До {MAX_DISH_LENGTH} символов.",
    )
    st.caption(f"{len(dish)}/{MAX_DISH_LENGTH} символов")

    people_column, format_column = st.columns(2)
    with people_column:
        people = st.selectbox("На сколько человек?", PEOPLE_OPTIONS, index=1)
    with format_column:
        answer_format = st.selectbox("Как оформить ответ?", FORMAT_OPTIONS, index=0)

    submitted = st.form_submit_button(
        "Сгенерировать список покупок",
        use_container_width=True,
    )

if submitted:
    try:
        with st.spinner("Собираем список…"):
            result = generate_shopping_list_sync(dish, people, answer_format)
    except UserFacingError as exc:
        st.error(str(exc), icon="⚠️")
    else:
        st.success("Список готов.", icon="✅")
        st.markdown('<p class="result-label">Результат</p>', unsafe_allow_html=True)
        st.markdown(result)

st.caption("Данные доступа читаются из переменных окружения и не отображаются в интерфейсе.")
