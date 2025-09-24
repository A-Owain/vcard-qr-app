# =========================
# Landing page renderer
# =========================
qs = st.experimental_get_query_params()

# Landing: Contact Card
if qs.get("view", [""])[0] == "landing_contact":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("📇 Contact Card")
    name = qs.get("name", [""])[0]
    if name:
        st.subheader(name)

    vcf_data = qs.get("vcf", [""])[0]
    wa       = qs.get("wa", [""])[0]
    site     = qs.get("site", [""])[0]
    mailto   = qs.get("mailto", [""])[0]
    tel      = qs.get("tel", [""])[0]

    cols = st.columns(2)
    with cols[0]:
        if vcf_data:
            st.link_button("💾 Save Contact", vcf_data, use_container_width=True)
        if site:
            st.link_button("🌐 Website", site, use_container_width=True)
    with cols[1]:
        if wa:
            st.link_button("💬 WhatsApp", wa, use_container_width=True)
        if mailto:
            st.link_button("✉️ Email", mailto, use_container_width=True)
        if tel:
            st.link_button("📞 Call", tel, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Landing: Link Hub
if qs.get("view", [""])[0] == "landing_links":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🔗 Quick Links")
    title = qs.get("title", ["My Links"])[0]
    st.subheader(title)

    links = json.loads(qs.get("links", ["[]"])[0])
    for text, url in links:
        st.link_button(text, url, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Landing: Event
if qs.get("view", [""])[0] == "landing_event":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("📅 Event Info")
    ev_title = qs.get("title", [""])[0]
    ev_date  = qs.get("date", [""])[0]
    ev_loc   = qs.get("loc", [""])[0]
    ev_desc  = qs.get("desc", [""])[0]

    if ev_title: st.subheader(ev_title)
    if ev_date: st.write(f"📌 Date: {ev_date}")
    if ev_loc: st.write(f"📍 Location: {ev_loc}")
    if ev_desc: st.write(ev_desc)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()
