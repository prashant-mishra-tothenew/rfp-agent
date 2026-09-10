from app.agents.rfp_analyzer import prepare_document_for_analysis


def test_prepare_document_keeps_short_text_unchanged():
    text = "Short RFP with one requirement."
    assert prepare_document_for_analysis(text, max_chars=1000) == text


def test_prepare_document_prioritizes_requirement_sections():
    filler = "Lorem ipsum " * 500
    requirement = "The vendor shall provide Drupal Commerce with PCI-DSS compliance."
    text = f"{filler}\n\n{requirement}"
    prepared = prepare_document_for_analysis(text, max_chars=2000)
    assert "Drupal Commerce" in prepared
    assert len(prepared) <= 2000
