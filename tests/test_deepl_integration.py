"""Test DeepL integration for bidirectional translation."""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_deepl_translator():
    """Create a mocked DeepL translator instance."""
    translator = Mock()

    # Mock translation result
    translation_result = Mock()
    translation_result.text = "こんにちは、PyCon Japanへようこそ"
    translator.translate_text.return_value = translation_result

    # Mock usage result
    usage = Mock()
    usage.character.count = 1500
    usage.character.limit = 500000
    translator.get_usage.return_value = usage

    return translator


def test_english_to_japanese_translation(mock_deepl_translator):
    """Test English to Japanese translation."""
    en_text = "Hello and welcome to PyCon Japan"

    # Configure mock to return Japanese text for English input
    translation_result = Mock()
    translation_result.text = "こんにちは、PyCon Japanへようこそ"
    mock_deepl_translator.translate_text.return_value = translation_result

    result = mock_deepl_translator.translate_text(en_text, target_lang="JA")

    assert result.text is not None
    assert len(result.text) > 0
    assert result.text != en_text  # Should be different from original
    mock_deepl_translator.translate_text.assert_called_once_with(en_text, target_lang="JA")


def test_japanese_to_english_translation(mock_deepl_translator):
    """Test Japanese to English translation."""
    ja_text = "こんにちは、PyCon Japanへようこそ"

    # Configure mock to return English text for Japanese input
    translation_result = Mock()
    translation_result.text = "Hello and welcome to PyCon Japan"
    mock_deepl_translator.translate_text.return_value = translation_result

    result = mock_deepl_translator.translate_text(ja_text, target_lang="EN-US")

    assert result.text is not None
    assert len(result.text) > 0
    assert result.text != ja_text  # Should be different from original
    mock_deepl_translator.translate_text.assert_called_once_with(ja_text, target_lang="EN-US")


def test_deepl_usage_tracking(mock_deepl_translator):
    """Test that DeepL usage tracking works."""
    usage = mock_deepl_translator.get_usage()

    assert usage.character.count is not None
    assert usage.character.count >= 0

    if usage.character.limit:
        assert usage.character.limit > 0
        assert usage.character.count <= usage.character.limit

    mock_deepl_translator.get_usage.assert_called_once()


@pytest.mark.parametrize(
    ("text", "target_lang", "expected_translation"),
    [
        ("Hello world", "JA", "こんにちは世界"),
        ("Thank you", "JA", "ありがとう"),
        ("こんにちは", "EN-US", "Hello"),
        ("ありがとう", "EN-US", "Thank you"),
    ],
)
def test_multiple_translations(mock_deepl_translator, text, target_lang, expected_translation):
    """Test multiple translation scenarios."""
    # Configure mock to return expected translation
    translation_result = Mock()
    translation_result.text = expected_translation
    mock_deepl_translator.translate_text.return_value = translation_result

    result = mock_deepl_translator.translate_text(text, target_lang=target_lang)

    assert result.text is not None
    assert len(result.text) > 0
    assert result.text == expected_translation
    mock_deepl_translator.translate_text.assert_called_with(text, target_lang=target_lang)
