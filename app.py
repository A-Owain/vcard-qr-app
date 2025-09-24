# =========================
# Landing page storage
# =========================
import os, uuid

def save_landing(data: dict, page_id: str):
    os.makedirs("landing_pages", exist_ok=True)
    with open(f"landing_pages/{page_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_landing(page_id: str):
    try:
        with open(f"landing_pages/{page_id}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

# =========================
# Landing page renderer
# =========================
qs = st.query_params
if "landing" in qs:
    page_id = qs["landing"][0]
    data = load_landing(page_id)
    if not data:
        st.error("Landing page not found.")
        st.stop()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title(data.get("name",""))
    st.write(data.get("notes",""))

    cols = st.columns(2)
    with cols[0]:
        if data.get("vcf"): st.link_button("💾 Save Contact", data["vcf"], use_container_width=True)
        if data.get("site"): st.link_button("🌐 Website", data["site"], use_container_width=True)
        if data.get("mailto"): st.link_button("✉️ Email", data["mailto"], use_container_width=True)
    with cols[1]:
        if data.get("wa"): st.link_button("💬 WhatsApp", data["wa"], use_container_width=True)
        if data.get("tel"): st.link_button("📞 Call", data["tel"], use_container_width=True)

    if data.get("audio"):
        st.divider()
        st.subheader("🔊 Audio Greeting")
        if data["audio"].startswith("data:audio"):
            st.audio(data["audio"])
        else:
            st.link_button("▶️ Play Audio", data["audio"], use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# =========================
# Landing Page Creator (tab)
# =========================
with tabs[3]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.header("Hosted Landing Page (One QR → Many Actions)")

    en_first = st.text_input("First Name", key="lp_first")
    en_last  = st.text_input("Last Name", key="lp_last")
    phone    = st.text_input("Phone (Work)", key="lp_phone")
    email    = st.text_input("Email", key="lp_email")
    website  = st.text_input("Website", key="lp_site")
    wa_num   = st.text_input("WhatsApp (digits only)", key="lp_wa")
    tel_num  = st.text_input("Tel Number", key="lp_tel")
    notes    = st.text_area("Notes", key="lp_notes")

    audio_file = st.file_uploader("Optional Audio (MP3/WAV)", type=["mp3","wav"], key="lp_audio")
    audio_uri = ""
    if audio_file:
        raw = audio_file.read()
        mt = "audio/mpeg" if audio_file.name.endswith(".mp3") else "audio/wav"
        audio_uri = short_data_uri(raw, mt, max_len=80_000) or ""

    if st.button("Save Landing Page & Generate QR", key="lp_btn"):
        vcard = build_vcard_core("3.0", en_first, en_last, "", "", phone, "", email, website, notes)
        vcf_b64 = base64.b64encode(vcard.encode("utf-8")).decode("ascii")
        vcf_uri = f"data:text/vcard;base64,{vcf_b64}"

        wa_url  = f"https://wa.me/{wa_num}" if wa_num else ""
        mailto  = f"mailto:{email}" if email else ""
        tel     = f"tel:{tel_num}" if tel_num else ""

        page_id = sanitize_filename(f"{en_first}_{en_last}_{datetime.now().strftime('%Y%m%d')}")
        data = {
            "name": f"{en_first} {en_last}",
            "notes": notes,
            "vcf": vcf_uri,
            "wa": wa_url,
            "site": website,
            "mailto": mailto,
            "tel": tel,
            "audio": audio_uri,
        }
        save_landing(data, page_id)

        base = current_app_url().rstrip("/")
        landing_url = f"{base}?landing={page_id}" if base else f"?landing={page_id}"
        st.text_input("Landing Page URL", landing_url, key="lp_url")

        # QR
        img = make_qr_image(landing_url, "M (15%)", 10, 4, as_svg=False)
        buf = io.BytesIO(); img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption="Landing QR")
        st.download_button("⬇️ Download QR (PNG)", buf.getvalue(),
                           file_name=f"{page_id}_qr.png", mime="image/png")
    st.markdown('</div>', unsafe_allow_html=True)
