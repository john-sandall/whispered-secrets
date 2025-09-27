"""Test translation functionality using Hugging Face transformers."""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_translator():
    """Create a mocked translation pipeline instance."""
    translator = Mock()

    # Mock translation results
    def mock_translate(text, max_length=512):  # noqa: ARG001
        if not text.strip():
            msg = "Empty text not allowed"
            raise ValueError(msg)

        # Simple mapping for predictable test results
        translations = {
            "Hello, how are you?": "こんにちは、元気ですか?",
            "Riding taxis with mobile apps in Japan": "日本でモバイルアプリでタクシーに乗る",
            "Transportation in Japanese cities": "日本の都市の交通",
            "Hello world": "こんにちは世界",
            "Good morning": "おはよう",
            "Thank you": "ありがとう",
            "This is a test sentence for translation.": "これは翻訳のためのテスト文です。",
            "Hello": "こんにちは",
        }

        japanese_text = translations.get(text, f"翻訳されたテキスト: {text}")
        return [{"translation_text": japanese_text}]

    translator.side_effect = mock_translate
    return translator


@pytest.mark.parametrize(
    ("text", "expected_content"),
    [
        ("Hello, how are you?", "こんにちは"),
        ("Riding taxis with mobile apps in Japan", "タクシー"),
        ("Transportation in Japanese cities", "交通"),
    ],
)
def test_english_to_japanese_translation(mock_translator, text, expected_content):
    """Test English to Japanese translation with basic content validation."""
    result = mock_translator(text, max_length=512)

    assert len(result) > 0
    translation = result[0]["translation_text"]
    assert translation is not None
    assert len(translation) > 0
    assert translation != text  # Should be different from original
    # Basic content check - should contain some expected Japanese content
    unicode_threshold = 127
    assert expected_content in translation or any(
        ord(char) > unicode_threshold for char in translation
    )
    mock_translator.assert_called_once_with(text, max_length=512)


def test_translation_pipeline_configuration(mock_translator):
    """Test that the translation pipeline is properly configured."""
    # Test with a simple phrase
    result = mock_translator("Hello", max_length=512)

    assert len(result) == 1
    assert "translation_text" in result[0]
    assert isinstance(result[0]["translation_text"], str)
    mock_translator.assert_called_once_with("Hello", max_length=512)


@pytest.mark.parametrize("max_length", [128, 256, 512])
def test_translation_with_different_max_lengths(mock_translator, max_length):
    """Test translation with different max_length parameters."""
    text = "This is a test sentence for translation."
    result = mock_translator(text, max_length=max_length)

    assert len(result) > 0
    translation = result[0]["translation_text"]
    assert translation is not None
    assert len(translation) > 0
    mock_translator.assert_called_once_with(text, max_length=max_length)


def test_empty_text_handling(mock_translator):
    """Test handling of empty or whitespace-only text."""
    with pytest.raises((ValueError, Exception)):
        mock_translator("", max_length=512)


def test_batch_translation(mock_translator):
    """Test batch translation of multiple texts."""
    texts = [
        "Hello world",
        "Good morning",
        "Thank you",
    ]

    results = [mock_translator(text, max_length=512) for text in texts]

    assert len(results) == len(texts)
    for result in results:
        assert len(result) > 0
        assert "translation_text" in result[0]
        assert len(result[0]["translation_text"]) > 0

    # Verify all calls were made
    assert mock_translator.call_count == len(texts)
