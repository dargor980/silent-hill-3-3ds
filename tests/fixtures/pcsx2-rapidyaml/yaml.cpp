#include <ryml.hpp>
#include <ryml_std.hpp>

#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}

std::string read_file(const char* path) {
    std::ifstream input(path, std::ios::binary);
    require(input.good(), "cannot read own fixture");
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

void structure(ryml::Tree const& tree) {
    auto root = tree.rootref();
    require(root.is_map() && root.num_children() == 1, "root shape");
    require(root.has_child("profile"), "profile missing");
    auto profile = root["profile"];
    require(profile.is_map() && profile.num_children() == 8, "profile shape");
    require(profile["title"].val() == "Prueba de cámara: áéíóú ñ", "UTF-8 scalar");
    require(profile["language"].val() == "es", "language");
    require(profile["empty"].val().empty(), "empty quoted scalar");
    require(!profile["empty"].val_is_null(), "empty quoted scalar is not null");
    bool enabled = false;
    int attempts = 0, offset = 0;
    double scale = 0;
    profile["enabled"] >> enabled;
    profile["attempts"] >> attempts;
    profile["offset"] >> offset;
    profile["scale"] >> scale;
    require(enabled && attempts == 3 && offset == -12, "scalar conversion");
    require(std::abs(scale - 1.25) < 1e-12, "floating conversion");
    require(profile["paths"].is_seq() && profile["paths"].num_children() == 2, "sequence shape");
    require(profile["paths"][0].val() == "inicio", "first element");
    require(profile["paths"][1].val() == "sala: norte", "quoted punctuation");
    require(!profile.has_child("missing"), "missing key unexpectedly present");
}

void ownership(std::string input) {
    auto arena = ryml::parse_in_arena(ryml::to_csubstr(input));
    input.assign(input.size(), '#');
    structure(arena); // Still valid after the caller's bytes change.
    std::string inplace = "key: retained\n";
    auto view = ryml::parse_in_place(ryml::to_substr(inplace));
    auto scalar = view["key"].val();
    auto begin = reinterpret_cast<std::uintptr_t>(inplace.data());
    auto address = reinterpret_cast<std::uintptr_t>(scalar.str);
    require(address >= begin && address + scalar.len <= begin + inplace.size(), "in-place storage");
    require(scalar == "retained", "in-place value");
    inplace[static_cast<std::size_t>(address - begin)] = 'R';
    require(view["key"].val() == "Retained", "in-place view must reflect live storage");
}

void roundtrip(ryml::Tree tree) {
    tree["profile"]["attempts"] << 7;
    tree["profile"]["paths"].append_child() << "salida";
    std::string note = "Texto con : y #; línea\nsegunda";
    tree["profile"]["note"] << note;
    note.assign(note.size(), '!'); // Serialized value belongs to the tree arena.
    auto output = ryml::emitrs_yaml<std::string>(tree);
    auto restored = ryml::parse_in_arena(ryml::to_csubstr(output));
    require(restored["profile"].num_children() == 9, "roundtrip map size");
    int attempts = 0;
    restored["profile"]["attempts"] >> attempts;
    require(attempts == 7, "roundtrip modified integer");
    require(restored["profile"]["paths"].num_children() == 3, "roundtrip sequence size");
    require(restored["profile"]["paths"][2].val() == "salida", "roundtrip appended item");
    require(restored["profile"]["note"].val() == "Texto con : y #; línea\nsegunda", "roundtrip escaped scalar");
    // Recheck every original field after undoing the deliberate mutations.
    restored["profile"]["attempts"] << 3;
    restored["profile"]["paths"].remove_child(2);
    restored["profile"].remove_child("note");
    structure(restored);
}

void bounds(ryml::Tree const& tree) {
    auto needed = ryml::emit_yaml(tree, ryml::substr{}, false);
    require(needed.str == nullptr && needed.len > 8, "output size query");
    std::array<char, 10> tiny;
    tiny.fill('@');
    auto small = ryml::emit_yaml(tree, ryml::substr(tiny.data() + 1, 8), false);
    require(small.str == nullptr && small.len == needed.len, "insufficient capacity contract");
    require(tiny.front() == '@' && tiny.back() == '@', "small output guards");
    std::vector<char> exact(needed.len + 2, '@');
    auto written = ryml::emit_yaml(tree, ryml::substr(exact.data() + 1, needed.len));
    require(written.str == exact.data() + 1 && written.len == needed.len, "exact output size");
    require(exact.front() == '@' && exact.back() == '@', "exact output guards");
    structure(ryml::parse_in_arena(ryml::csubstr(written.str, written.len)));
}

struct ParseFailure : std::runtime_error {
    std::size_t line, column;
    ParseFailure(ryml::csubstr message, ryml::ErrorDataParse const& data)
        : std::runtime_error(std::string(message.str, message.len)),
          line(data.ymlloc.line), column(data.ymlloc.col) {}
};

class ParseCallbackScope {
    ryml::Callbacks previous_ = ryml::get_callbacks();
    static void fail(ryml::csubstr message, ryml::ErrorDataParse const& data, void* user) {
        ++*static_cast<unsigned*>(user);
        throw ParseFailure(message, data);
    }
public:
    explicit ParseCallbackScope(unsigned& count) {
        auto configured = previous_;
        configured.set_user_data(&count).set_error_parse(&fail);
        ryml::set_callbacks(configured);
    }
    ParseCallbackScope(ParseCallbackScope const&) = delete;
    ParseCallbackScope& operator=(ParseCallbackScope const&) = delete;
    ~ParseCallbackScope() { ryml::set_callbacks(previous_); }
};

void invalid() {
    auto before = ryml::get_callbacks();
    unsigned calls = 0;
    for (auto text : {"value: [one, two\n", "value: \"unterminated\n"}) {
        bool rejected = false;
        try {
            ParseCallbackScope scope(calls);
            auto tree = ryml::parse_in_arena("invalid-own.yaml", ryml::to_csubstr(text));
            (void)tree;
        } catch (ParseFailure const& failure) {
            rejected = true;
            require(*failure.what() != '\0', "missing parse diagnostic");
            require(failure.line != ryml::npos && failure.column != ryml::npos, "missing parse location");
        }
        require(rejected, "malformed YAML accepted");
        auto after = ryml::get_callbacks();
        require(after.m_user_data == before.m_user_data && after.m_error_parse == before.m_error_parse,
                "callback restoration");
        auto recovered = ryml::parse_in_arena("value: recovered\n");
        require(recovered["value"].val() == "recovered", "parse after rejection");
    }
    require(calls == 2, "parse callback count");
}
} // namespace

int main(int argc, char** argv) {
    try {
        require(argc == 3, "usage: fixture case own-yaml");
        require(std::string(RYML_VERSION) == "0.12.1" && ryml::version() == "0.12.1", "header/runtime version");
        auto input = read_file(argv[2]);
        auto tree = ryml::parse_in_arena(ryml::to_csubstr(input));
        std::string selected = argv[1];
        if (selected == "structure") structure(tree);
        else if (selected == "ownership") ownership(input);
        else if (selected == "roundtrip") roundtrip(std::move(tree));
        else if (selected == "bounds") bounds(tree);
        else if (selected == "invalid") invalid();
        else throw std::runtime_error("unknown case");
        std::cout << selected << ": passed\n";
        return 0;
    } catch (std::exception const& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
