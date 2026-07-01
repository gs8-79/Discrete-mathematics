#include "parser.h"

#include <codecvt>
#include <iostream>
#include <locale>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using Assignment = std::unordered_map<std::string, bool>;
using Clause = std::vector<int>;
using CNF = std::vector<Clause>;

namespace {

void collect_vars(const Node* node, std::set<std::string>& vars) {
    if (const auto* v = dynamic_cast<const Var*>(node)) {
        vars.insert(v->name);
    } else if (const auto* n = dynamic_cast<const Not*>(node)) {
        collect_vars(n->child.get(), vars);
    } else if (const auto* a = dynamic_cast<const And*>(node)) {
        for (const auto& child : a->children) collect_vars(child.get(), vars);
    } else if (const auto* o = dynamic_cast<const Or*>(node)) {
        for (const auto& child : o->children) collect_vars(child.get(), vars);
    } else if (const auto* i = dynamic_cast<const Implies*>(node)) {
        collect_vars(i->left.get(), vars);
        collect_vars(i->right.get(), vars);
    } else if (const auto* iff = dynamic_cast<const Iff*>(node)) {
        collect_vars(iff->left.get(), vars);
        collect_vars(iff->right.get(), vars);
    }
}

bool eval_node(const Node* node, const Assignment& assignment) {
    if (const auto* v = dynamic_cast<const Var*>(node)) {
        auto it = assignment.find(v->name);
        if (it == assignment.end()) throw std::runtime_error("Missing assignment: " + v->name);
        return it->second;
    }
    if (const auto* n = dynamic_cast<const Not*>(node)) return !eval_node(n->child.get(), assignment);
    if (const auto* a = dynamic_cast<const And*>(node)) {
        for (const auto& child : a->children) {
            if (!eval_node(child.get(), assignment)) return false;
        }
        return true;
    }
    if (const auto* o = dynamic_cast<const Or*>(node)) {
        for (const auto& child : o->children) {
            if (eval_node(child.get(), assignment)) return true;
        }
        return false;
    }
    if (const auto* i = dynamic_cast<const Implies*>(node)) {
        return !eval_node(i->left.get(), assignment) || eval_node(i->right.get(), assignment);
    }
    if (const auto* iff = dynamic_cast<const Iff*>(node)) {
        return eval_node(iff->left.get(), assignment) == eval_node(iff->right.get(), assignment);
    }
    throw std::runtime_error("Unknown AST node");
}

std::unique_ptr<Node> parse_formula(const std::string& input) {
    Tokenizer tokenizer(input);
    std::vector<Token> tokens = tokenizer.tokenize();
    for (const Token& token : tokens) {
        if (token.type == TOK_ERROR) throw std::runtime_error(token.value);
    }
    Parser parser(tokens);
    return std::unique_ptr<Node>(parser.parse());
}

std::string cnf_json(const CNF& cnf, const std::vector<std::string>& vars) {
    std::string json = "{\"clauses\":[";
    for (size_t i = 0; i < cnf.size(); ++i) {
        if (i) json += ",";
        json += "[";
        for (size_t j = 0; j < cnf[i].size(); ++j) {
            if (j) json += ",";
            json += std::to_string(cnf[i][j]);
        }
        json += "]";
    }
    json += "],\"var_map\":{";
    for (size_t i = 0; i < vars.size(); ++i) {
        if (i) json += ",";
        json += "\"" + escape_json(vars[i]) + "\":" + std::to_string(i + 1);
    }
    json += "}}";
    return json;
}

std::string build_cnf_json(const Node* root) {
    std::set<std::string> var_set;
    collect_vars(root, var_set);
    std::vector<std::string> vars(var_set.begin(), var_set.end());
    const size_t row_count = vars.empty() ? 1ULL : (1ULL << vars.size());
    CNF cnf;

    for (size_t row = 0; row < row_count; ++row) {
        Assignment assignment;
        for (size_t i = 0; i < vars.size(); ++i) {
            bool value = ((row >> (vars.size() - i - 1)) & 1ULL) == 0;
            assignment[vars[i]] = value;
        }
        if (!eval_node(root, assignment)) {
            Clause clause;
            for (size_t i = 0; i < vars.size(); ++i) {
                clause.push_back(assignment[vars[i]] ? -static_cast<int>(i + 1)
                                                     : static_cast<int>(i + 1));
            }
            cnf.push_back(clause);
        }
    }

    return cnf_json(cnf, vars);
}

std::string join_args(int argc, char* argv[]) {
    std::string input;
    for (int i = 1; i < argc; ++i) {
        if (i > 1) input += " ";
        input += argv[i];
    }
    return input;
}

#ifdef _WIN32
std::string join_args(int argc, wchar_t* argv[]) {
    std::wstring_convert<std::codecvt_utf8_utf16<wchar_t>> converter;
    std::string input;
    for (int i = 1; i < argc; ++i) {
        if (i > 1) input += " ";
        input += converter.to_bytes(argv[i]);
    }
    return input;
}
#endif

int run(const std::string& input) {
    try {
        if (input.empty()) throw std::runtime_error("Input is empty");
        std::unique_ptr<Node> root = parse_formula(input);
        std::cout << build_cnf_json(root.get()) << '\n';
        return 0;
    } catch (const std::exception& ex) {
        std::cout << error_json(ex.what()) << '\n';
        return 1;
    }
}

}  // namespace

#ifdef _WIN32
int wmain(int argc, wchar_t* argv[]) {
    std::string input;
    if (argc > 1) {
        input = join_args(argc, argv);
    } else {
        std::getline(std::cin, input);
    }
    return run(input);
}
#else
int main(int argc, char* argv[]) {
    std::string input = argc > 1 ? join_args(argc, argv) : "";
    if (argc <= 1) std::getline(std::cin, input);
    return run(input);
}
#endif
