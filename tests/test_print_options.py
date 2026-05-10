from app.models.print_options import PrintOptions
from app.services.lpoptions_parser import parse_lpoptions


def test_parse_lpoptions() -> None:
    capabilities = parse_lpoptions(
        "PageSize/Media Size: *A4 Letter\n"
        "ColorModel/Color Model: *Gray RGB\n"
        "Duplex/2-Sided Printing: *None DuplexNoTumble DuplexTumble\n"
    )

    assert capabilities["PageSize"] == {"A4", "Letter"}
    assert capabilities["ColorModel"] == {"Gray", "RGB"}
    assert capabilities["Duplex"] == {"None", "DuplexNoTumble", "DuplexTumble"}


def test_print_options_map_conservative_values() -> None:
    options = PrintOptions(
        copies=2,
        paper_size="A4",
        duplex="long-edge",
        orientation="portrait",
        color_mode="monochrome",
        quality="high",
    )

    mapped = options.to_cups_options(
        {
            "PageSize": {"A4", "Letter"},
            "Duplex": {"None", "DuplexNoTumble", "DuplexTumble"},
            "ColorModel": {"Gray", "RGB"},
            "Quality": {"Draft", "Normal", "High"},
        }
    )

    assert mapped.applied_options["copies"] == "2"
    assert mapped.applied_options["PageSize"] == "A4"
    assert mapped.applied_options["Duplex"] == "DuplexNoTumble"
    assert mapped.applied_options["ColorModel"] == "Gray"
    assert mapped.applied_options["Quality"] == "High"
    assert mapped.unsupported_options == []


def test_print_options_drop_unsupported_values() -> None:
    mapped = PrintOptions(paper_size="Letter", color_mode="color").to_cups_options(
        {"PageSize": {"A4"}, "ColorModel": {"Gray"}}
    )

    assert "paper_size" in mapped.unsupported_options
    assert "color_mode" in mapped.unsupported_options
    assert mapped.applied_options == {"copies": "1"}
