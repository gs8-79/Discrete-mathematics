#ifndef AST_H
#define AST_H

#include <cstddef>
#include <iomanip>
#include <memory>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

enum NodeType { NODE_VAR, NODE_NOT, NODE_AND, NODE_OR, NODE_IMPLIES, NODE_IFF };

struct Node {
    NodeType type;
    virtual ~Node() = default;
    virtual std::string to_json() const = 0;
};

struct Var : Node {
    std::string name;
    explicit Var(const std::string& n) : name(n) { type = NODE_VAR; }
    std::string to_json() const override;
};

struct Not : Node {
    std::unique_ptr<Node> child;
    explicit Not(Node* c) : child(c) { type = NODE_NOT; }
    std::string to_json() const override;
};

struct And : Node {
    std::vector<std::unique_ptr<Node>> children;
    And() { type = NODE_AND; }
    void add(Node* n) { children.emplace_back(n); }
    std::string to_json() const override;
};

struct Or : Node {
    std::vector<std::unique_ptr<Node>> children;
    Or() { type = NODE_OR; }
    void add(Node* n) { children.emplace_back(n); }
    std::string to_json() const override;
};

struct Implies : Node {
    std::unique_ptr<Node> left;
    std::unique_ptr<Node> right;
    Implies(Node* l, Node* r) : left(l), right(r) { type = NODE_IMPLIES; }
    std::string to_json() const override;
};

struct Iff : Node {
    std::unique_ptr<Node> left;
    std::unique_ptr<Node> right;
    Iff(Node* l, Node* r) : left(l), right(r) { type = NODE_IFF; }
    std::string to_json() const override;
};

inline std::string escape_json(const std::string& s) {
    std::ostringstream out;
    for (unsigned char c : s) {
        switch (c) {
            case '"': out << "\\\""; break;
            case '\\': out << "\\\\"; break;
            case '\b': out << "\\b"; break;
            case '\f': out << "\\f"; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default:
                if (c < 0x20) {
                    out << "\\u" << std::hex << std::setw(4)
                        << std::setfill('0') << static_cast<int>(c);
                } else {
                    out << static_cast<char>(c);
                }
        }
    }
    return out.str();
}

inline std::string Var::to_json() const {
    return "{\"type\":\"var\",\"name\":\"" + escape_json(name) + "\"}";
}

inline std::string Not::to_json() const {
    return "{\"type\":\"not\",\"child\":" + child->to_json() + "}";
}

inline std::string And::to_json() const {
    std::string s = "{\"type\":\"and\",\"children\":[";
    for (size_t i = 0; i < children.size(); ++i) {
        if (i) s += ",";
        s += children[i]->to_json();
    }
    return s + "]}";
}

inline std::string Or::to_json() const {
    std::string s = "{\"type\":\"or\",\"children\":[";
    for (size_t i = 0; i < children.size(); ++i) {
        if (i) s += ",";
        s += children[i]->to_json();
    }
    return s + "]}";
}

inline std::string Implies::to_json() const {
    return "{\"type\":\"implies\",\"left\":" + left->to_json()
         + ",\"right\":" + right->to_json() + "}";
}

inline std::string Iff::to_json() const {
    return "{\"type\":\"iff\",\"left\":" + left->to_json()
         + ",\"right\":" + right->to_json() + "}";
}

inline std::string clauses_to_json(
    const std::vector<std::vector<int>>& clauses,
    const std::unordered_map<std::string, int>& var_map) {
    std::string s = "{\"clauses\":[";
    for (size_t i = 0; i < clauses.size(); ++i) {
        if (i) s += ",";
        s += "[";
        for (size_t j = 0; j < clauses[i].size(); ++j) {
            if (j) s += ",";
            s += std::to_string(clauses[i][j]);
        }
        s += "]";
    }
    s += "],\"var_map\":{";
    bool first = true;
    for (const auto& kv : var_map) {
        if (!first) s += ",";
        first = false;
        s += "\"" + escape_json(kv.first) + "\":" + std::to_string(kv.second);
    }
    return s + "}}";
}

inline std::string truth_table_to_json(
    const std::vector<std::string>& vars,
    const std::vector<std::pair<std::unordered_map<std::string, bool>, bool>>& rows,
    bool satisfiable,
    bool tautology,
    bool contradiction) {
    std::string s = "{\"variables\":[";
    for (size_t i = 0; i < vars.size(); ++i) {
        if (i) s += ",";
        s += "\"" + escape_json(vars[i]) + "\"";
    }
    s += "],\"rows\":[";
    for (size_t i = 0; i < rows.size(); ++i) {
        if (i) s += ",";
        s += "{";
        bool first = true;
        for (const auto& kv : rows[i].first) {
            if (!first) s += ",";
            first = false;
            s += "\"" + escape_json(kv.first) + "\":"
               + std::string(kv.second ? "true" : "false");
        }
        s += ",\"result\":" + std::string(rows[i].second ? "true" : "false") + "}";
    }
    s += "],\"satisfiable\":" + std::string(satisfiable ? "true" : "false");
    s += ",\"tautology\":" + std::string(tautology ? "true" : "false");
    s += ",\"contradiction\":" + std::string(contradiction ? "true" : "false") + "}";
    return s;
}

inline std::string dpll_result_to_json(
    bool sat,
    const std::unordered_map<std::string, bool>& assignment) {
    std::string s = "{\"sat\":" + std::string(sat ? "true" : "false")
                  + ",\"assignment\":{";
    bool first = true;
    for (const auto& kv : assignment) {
        if (!first) s += ",";
        first = false;
        s += "\"" + escape_json(kv.first) + "\":"
           + std::string(kv.second ? "true" : "false");
    }
    return s + "}}";
}

inline std::string error_json(const std::string& msg) {
    return "{\"error\":\"" + escape_json(msg) + "\"}";
}

#endif
