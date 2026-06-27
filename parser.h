#ifndef PARSER_H
#define PARSER_H

#include "ast.h"

#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>

enum TokenType {
    TOK_VAR,
    TOK_NOT,
    TOK_AND,
    TOK_OR,
    TOK_IMPLIES,
    TOK_IFF,
    TOK_LPAREN,
    TOK_RPAREN,
    TOK_END,
    TOK_ERROR
};

struct Token {
    TokenType type;
    std::string value;
    Token(TokenType t, const std::string& v = "") : type(t), value(v) {}
};

class Tokenizer {
public:
    explicit Tokenizer(const std::string& input);
    std::vector<Token> tokenize();

private:
    std::string src;
    size_t pos;

    void skip_whitespace();
    std::string read_utf8_char();
    bool match(const std::string& s);
    Token next_token();
};

class Parser {
public:
    explicit Parser(const std::vector<Token>& tokens);
    Node* parse();

private:
    std::vector<Token> tokens;
    size_t pos;

    const Token& current() const;
    void advance();
    void expect(TokenType type);

    Node* parse_iff();
    Node* parse_implies();
    Node* parse_or();
    Node* parse_and();
    Node* parse_not();
    Node* parse_primary();
};

#endif
