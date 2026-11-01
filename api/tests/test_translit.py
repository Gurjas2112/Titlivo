from titlivo.services import translit


def test_latin_readable():
    assert translit.to_latin("सुनील पाटील") == "Sunil Patil"
    assert translit.to_latin("ಶಿವಕುಮಾರ್ ಗೌಡ") == "Shivakumar Gauda"
    assert translit.to_latin("દેસાઈ પટેલ") == "Desai Patel"


def test_name_key_cross_script():
    assert translit.name_key("सुनील पाटील") == translit.name_key("Sunil Patil") == translit.name_key("Suneel Paatil")


def test_mask():
    assert translit.mask("Sunil Patil") == "S. P****"
