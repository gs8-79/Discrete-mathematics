#include "parser.h"

#include <cctype>
#include <iostream>
#include <memory>
#include <stdexcept>

namespace {

const char* token_name(TokenType type) {
    switch (type) {
        case TOK_VAR: return "variable";
        case TOK_NOT: return "not";
        case TOK_AND: return "and";
        case TOK_OR: return "or";
        case TOK_IMPLIES: return "implies";
        case TOK_IFF: return "iff";
        case TOK_LPAREN: return "left parenthesis";
        case TOK_RPAREN: return "right parenthesis";
        case TOK_END: return "end of input";
        case TOK_ERROR: return "error";
    }
    return "unknown";
}

bool is_var_start(unsigned char c) {
    return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
}

bool is_var_char(unsigned char c) {
    return is_var_start(c) || (c >= '0' && c <= '9') || c == '_';
}

std::string describe_token(const Token& token) {
    if (!token.value.empty()) {
        return std::string(token_name(token.type)) + " '" + token.value + "'";
    }
    return token_name(token.type);
}

std::string join_arguments(int argc, char* argv[]) {
    std::string input;
    for (int i = 1; i < argc; ++i) {
        if (i > 1) input += " ";
        input += argv[i];
    }
    return input;
}

}  // namespace

Tokenizer::Tokenizer(const std::string& input) : src(input), pos(0) {}

void Tokenizer::skip_whitespace() {
    while (pos < src.size() &&
           std::isspace(static_cast<unsigned char>(src[pos]))) {
        ++pos;
    }
}

std::string Tokenizer::read_utf8_char() {
    if (pos >= src.size()) return "";

    unsigned char c = static_cast<unsigned char>(src[pos]);
    size_t len = 1;
    if ((c & 0x80) == 0) {
        len = 1;
    } else if ((c & 0xE0) == 0xC0) {
        len = 2;
    } else if ((c & 0xF0) == 0xE0) {
        len = 3;
    } else if ((c & 0xF8) == 0xF0) {
        len = 4;
    } else {
        ++pos;
        return std::string(1, static_cast<char>(c));
    }

    if (pos + len > src.size()) {
        std::string result = src.substr(pos);
        pos = src.size();
        return result;
    }

    for (size_t i = 1; i < len; ++i) {
        unsigned char next = static_cast<unsigned char>(src[pos + i]);
        if ((next & 0xC0) != 0x80) {
            ++pos;
            return std::string(1, static_cast<char>(c));
        }
    }

    std::string result = src.substr(pos, len);
    pos += len;
    return result;
}

bool Tokenizer::match(const std::string& s) {
    if (src.compare(pos, s.size(), s) == 0) {
        pos += s.size();
        return true;
    }
    return false;
}

Token Tokenizer::next_token() {
    skip_whitespace();
    if (pos >= src.size()) return Token(TOK_END);

    unsigned char c = static_cast<unsigned char>(src[pos]);

    if (is_var_start(c)) {
        size_t start = pos++;
        while (pos < src.size() &&
               is_var_char(static_cast<unsigned char>(src[pos]))) {
            ++pos;
        }
        return Token(TOK_VAR, src.substr(start, pos - start));
    }

    if (c == '_' || (c >= '0' && c <= '9')) {
        std::string bad = read_utf8_char();
        return Token(TOK_ERROR, "Invalid variable start: " + bad);
    }

    if (match("\xE2\x86\x94")) return Token(TOK_IFF);      // U+2194
    if (match("\xE2\x86\x92")) return Token(TOK_IMPLIES);  // U+2192
    if (match("<->")) return Token(TOK_IFF);
    if (match("<=>")) return Token(TOK_IFF);
    if (match("->")) return Token(TOK_IMPLIES);
    if (match("=>")) return Token(TOK_IMPLIES);
    if (match("\xE2\x88\xA7")) return Token(TOK_AND);      // U+2227
    if (match("\xE2\x88\xA8")) return Token(TOK_OR);       // U+2228
    if (match("\xC2\xAC")) return Token(TOK_NOT);          // U+00AC
    if (match("&&")) return Token(TOK_AND);
    if (match("||")) return Token(TOK_OR);
    if (match("!")) return Token(TOK_NOT);
    if (match("~")) return Token(TOK_NOT);
    if (match("&")) return Token(TOK_AND);
    if (match("|")) return Token(TOK_OR);

    if (c == '(') {
        ++pos;
        return Token(TOK_LPAREN);
    }
    if (c == ')') {
        ++pos;
        return Token(TOK_RPAREN);
    }

    std::string unknown = read_utf8_char();
    return Token(TOK_ERROR, "Illegal character: " + unknown);
}

std::vector<Token> Tokenizer::tokenize() {
    std::vector<Token> result;
    while (true) {
        Token token = next_token();
        result.push_back(token);
        if (token.type == TOK_END || token.type == TOK_ERROR) break;
    }
    return result;
}

Parser::Parser(const std::vector<Token>& toks) : tokens(toks), pos(0) {
    if (tokens.empty() || tokens.back().type != TOK_END) {
        tokens.emplace_back(TOK_END);
    }
}

const Token& Parser::current() const {
    if (pos >= tokens.size()) return tokens.back();
    return tokens[pos];
}

void Parser::advance() {
    if (pos + 1 < tokens.size()) {
        ++pos;
    }
}

void Parser::expect(TokenType type) {
    if (current().type != type) {
        throw std::runtime_error(
            std::string("Expected ") + token_name(type) +
            ", got " + describe_token(current()));
    }
    advance();
}

Node* Parser::parse_iff() {
    std::unique_ptr<Node> left(parse_implies());
    while (current().type == TOK_IFF) {
        advance();
        std::unique_ptr<Node> right(parse_implies());
        left.reset(new Iff(left.release(), right.release()));
    }
    return left.release();
}

Node* Parser::parse_implies() {
    std::unique_ptr<Node> left(parse_or());
    if (current().type == TOK_IMPLIES) {
        advance();
        std::unique_ptr<Node> right(parse_implies());
        return new Implies(left.release(), right.release());
    }
    return left.release();
}

Node* Parser::parse_or() {
    std::unique_ptr<Node> left(parse_and());
    while (current().type == TOK_OR) {
        advance();
        std::unique_ptr<Node> right(parse_and());
        if (auto* existing = dynamic_cast<Or*>(left.get())) {
            existing->add(right.release());
        } else {
            auto* node = new Or();
            node->add(left.release());
            node->add(right.release());
            left.reset(node);
        }
    }
    return left.release();
}

Node* Parser::parse_and() {
    std::unique_ptr<Node> left(parse_not());
    while (current().type == TOK_AND) {
        advance();
        std::unique_ptr<Node> right(parse_not());
        if (auto* existing = dynamic_cast<And*>(left.get())) {
            existing->add(right.release());
        } else {
            auto* node = new And();
            node->add(left.release());
            node->add(right.release());
            left.reset(node);
        }
    }
    return left.release();
}

Node* Parser::parse_not() {
    if (current().type == TOK_NOT) {
        advance();
        return new Not(parse_not());
    }
    return parse_primary();
}

Node* Parser::parse_primary() {
    const Token& token = current();
    if (token.type == TOK_VAR) {
        advance();
        return new Var(token.value);
    }

    if (token.type == TOK_LPAREN) {
        advance();
        std::unique_ptr<Node> expr(parse_iff());
        expect(TOK_RPAREN);
        return expr.release();
    }

    if (token.type == TOK_END) {
        throw std::runtime_error("Unexpected end of input");
    }
    if (token.type == TOK_ERROR) {
        throw std::runtime_error(token.value);
    }
    throw std::runtime_error("Unexpected token: " + describe_token(token));
}

Node* Parser::parse() {
    std::unique_ptr<Node> root(parse_iff());
    if (current().type != TOK_END) {
        std::string token = describe_token(current());
        throw std::runtime_error(
            "Unexpected token after complete expression: " + token);
    }
    return root.release();
}

#ifndef PARSER_NO_MAIN
namespace {

int run_parser(const std::string& input) {
    try {
        if (input.empty()) {
            throw std::runtime_error("Input is empty");
        }

        Tokenizer tokenizer(input);
        std::vector<Token> tokens = tokenizer.tokenize();
        for (const Token& token : tokens) {
            if (token.type == TOK_ERROR) {
                throw std::runtime_error(token.value);
            }
        }

        Parser parser(tokens);
        std::unique_ptr<Node> ast(parser.parse());
        std::cout << ast->to_json();
        return 0;
    } catch (const std::exception& ex) {
        std::cout << error_json(ex.what());
        return 1;
    }
}

}  // namespace

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <shellapi.h>
#ifdef _MSC_VER
#pragma comment(lib, "Shell32.lib")
#endif

namespace {

std::string wide_to_utf8(const wchar_t* value) {
    if (value == nullptr) return "";
    int length = static_cast<int>(wcslen(value));
    if (length == 0) return "";

    int needed = WideCharToMultiByte(
        CP_UTF8, 0, value, length, nullptr, 0, nullptr, nullptr);
    if (needed <= 0) return "";

    std::string result(static_cast<size_t>(needed), '\0');
    WideCharToMultiByte(
        CP_UTF8, 0, value, length, result.data(), needed, nullptr, nullptr);
    return result;
}

std::string read_windows_arguments() {
    int argc = 0;
    wchar_t** argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (argv == nullptr) return "";

    std::string input;
    for (int i = 1; i < argc; ++i) {
        if (i > 1) input += " ";
        input += wide_to_utf8(argv[i]);
    }
    LocalFree(argv);
    return input;
}

}  // namespace
#endif

int main(int argc, char* argv[]) {
    (void)argv;
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
#endif

    std::ios::sync_with_stdio(false);

    std::string input;
    if (argc > 1) {
#ifdef _WIN32
        input = read_windows_arguments();
#else
        input = join_arguments(argc, argv);
#endif
    } else {
        std::getline(std::cin, input);
    }

    return run_parser(input);
}
#endif
