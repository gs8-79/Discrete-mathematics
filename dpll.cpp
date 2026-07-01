#include "ast.h"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using Clause = std::vector<int>;
using CNF = std::vector<Clause>;
using VarMap = std::map<std::string, int>;
using IdAssignment = std::map<int, bool>;

struct CNFInput {
    CNF clauses;
    VarMap var_map;
};

namespace {

class JsonParser {
public:
    explicit JsonParser(const std::string& text) : text_(text), pos_(0) {}

    CNFInput parse() {
        CNFInput input;
        expect('{');
        bool saw_clauses = false;
        bool saw_var_map = false;
        while (true) {
            skip_ws();
            if (peek() == '}') break;
            std::string key = parse_string();
            expect(':');
            if (key == "clauses") {
                input.clauses = parse_clauses();
                saw_clauses = true;
            } else if (key == "var_map") {
                input.var_map = parse_var_map();
                saw_var_map = true;
            } else {
                throw std::runtime_error("Unknown key: " + key);
            }
            skip_ws();
            if (peek() == ',') {
                ++pos_;
                continue;
            }
            break;
        }
        expect('}');
        skip_ws();
        if (pos_ != text_.size()) throw std::runtime_error("Trailing data after JSON object");
        if (!saw_clauses) throw std::runtime_error("Missing clauses");
        if (!saw_var_map) throw std::runtime_error("Missing var_map");
        return input;
    }

private:
    std::string text_;
    size_t pos_;

    char peek() const {
        return pos_ < text_.size() ? text_[pos_] : '\0';
    }

    void skip_ws() {
        while (pos_ < text_.size() && std::isspace(static_cast<unsigned char>(text_[pos_]))) {
            ++pos_;
        }
    }

    void expect(char expected) {
        skip_ws();
        if (peek() != expected) {
            throw std::runtime_error(std::string("Expected '") + expected + "'");
        }
        ++pos_;
    }

    std::string parse_string() {
        expect('"');
        std::string result;
        while (true) {
            char c = peek();
            if (c == '\0') throw std::runtime_error("Unterminated string");
            ++pos_;
            if (c == '"') break;
            if (c == '\\') {
                char e = peek();
                if (e == '\0') throw std::runtime_error("Bad escape");
                ++pos_;
                if (e == '"' || e == '\\' || e == '/') result += e;
                else if (e == 'b') result += '\b';
                else if (e == 'f') result += '\f';
                else if (e == 'n') result += '\n';
                else if (e == 'r') result += '\r';
                else if (e == 't') result += '\t';
                else throw std::runtime_error("Unsupported escape sequence");
            } else {
                result += c;
            }
        }
        return result;
    }

    int parse_int() {
        skip_ws();
        bool neg = false;
        if (peek() == '-') {
            neg = true;
            ++pos_;
        }
        if (!std::isdigit(static_cast<unsigned char>(peek()))) {
            throw std::runtime_error("Expected integer");
        }
        int value = 0;
        while (std::isdigit(static_cast<unsigned char>(peek()))) {
            value = value * 10 + (peek() - '0');
            ++pos_;
        }
        return neg ? -value : value;
    }

    Clause parse_clause() {
        Clause clause;
        expect('[');
        while (true) {
            skip_ws();
            if (peek() == ']') break;
            clause.push_back(parse_int());
            skip_ws();
            if (peek() == ',') {
                ++pos_;
                continue;
            }
            break;
        }
        expect(']');
        return clause;
    }

    CNF parse_clauses() {
        CNF clauses;
        expect('[');
        while (true) {
            skip_ws();
            if (peek() == ']') break;
            clauses.push_back(parse_clause());
            skip_ws();
            if (peek() == ',') {
                ++pos_;
                continue;
            }
            break;
        }
        expect(']');
        return clauses;
    }

    VarMap parse_var_map() {
        VarMap vars;
        expect('{');
        while (true) {
            skip_ws();
            if (peek() == '}') break;
            std::string name = parse_string();
            expect(':');
            int id = parse_int();
            if (id <= 0) throw std::runtime_error("Variable id must be positive");
            vars[name] = id;
            skip_ws();
            if (peek() == ',') {
                ++pos_;
                continue;
            }
            break;
        }
        expect('}');
        return vars;
    }
};

bool set_assignment(IdAssignment& assignment, int var, bool value) {
    auto it = assignment.find(var);
    if (it != assignment.end()) return it->second == value;
    assignment[var] = value;
    return true;
}

bool simplify(const CNF& cnf, const IdAssignment& assignment, CNF& simplified) {
    simplified.clear();
    for (const Clause& clause : cnf) {
        bool satisfied = false;
        Clause next;
        for (int lit : clause) {
            int var = std::abs(lit);
            auto it = assignment.find(var);
            if (it == assignment.end()) {
                next.push_back(lit);
                continue;
            }
            bool lit_value = lit > 0 ? it->second : !it->second;
            if (lit_value) {
                satisfied = true;
                break;
            }
        }
        if (!satisfied) {
            if (next.empty()) return false;
            simplified.push_back(next);
        }
    }
    return true;
}

bool propagate_units(CNF& cnf, IdAssignment& assignment) {
    while (true) {
        bool found = false;
        for (const Clause& clause : cnf) {
            if (clause.empty()) return false;
            if (clause.size() == 1) {
                int lit = clause[0];
                int var = std::abs(lit);
                bool value = lit > 0;
                auto before = assignment.size();
                if (!set_assignment(assignment, var, value)) return false;
                CNF next;
                if (!simplify(cnf, assignment, next)) return false;
                cnf.swap(next);
                (void)before;
                found = true;
                break;
            }
        }
        if (!found) return true;
    }
}

bool assign_pure_literals(CNF& cnf, IdAssignment& assignment) {
    std::map<int, int> polarity;
    for (const Clause& clause : cnf) {
        for (int lit : clause) {
            int var = std::abs(lit);
            if (assignment.count(var)) continue;
            int sign = lit > 0 ? 1 : -1;
            if (!polarity.count(var)) polarity[var] = sign;
            else if (polarity[var] != sign) polarity[var] = 0;
        }
    }

    bool changed = false;
    for (const auto& kv : polarity) {
        if (kv.second == 0) continue;
        if (!set_assignment(assignment, kv.first, kv.second > 0)) return false;
        changed = true;
    }
    if (changed) {
        CNF next;
        if (!simplify(cnf, assignment, next)) return false;
        cnf.swap(next);
    }
    return true;
}

int choose_variable(const CNF& cnf, const IdAssignment& assignment) {
    std::map<int, int> freq;
    for (const Clause& clause : cnf) {
        for (int lit : clause) {
            int var = std::abs(lit);
            if (!assignment.count(var)) ++freq[var];
        }
    }
    int best = 0;
    int best_freq = -1;
    for (const auto& kv : freq) {
        if (kv.second > best_freq) {
            best = kv.first;
            best_freq = kv.second;
        }
    }
    return best;
}

bool dpll(CNF cnf, IdAssignment assignment, IdAssignment& result) {
    CNF simplified;
    if (!simplify(cnf, assignment, simplified)) return false;
    cnf.swap(simplified);

    while (true) {
        if (cnf.empty()) {
            result = assignment;
            return true;
        }
        if (!propagate_units(cnf, assignment)) return false;
        if (cnf.empty()) {
            result = assignment;
            return true;
        }
        size_t before = assignment.size();
        if (!assign_pure_literals(cnf, assignment)) return false;
        if (cnf.empty()) {
            result = assignment;
            return true;
        }
        if (assignment.size() == before) break;
    }

    int var = choose_variable(cnf, assignment);
    if (var == 0) {
        result = assignment;
        return true;
    }

    IdAssignment true_assignment = assignment;
    true_assignment[var] = true;
    if (dpll(cnf, true_assignment, result)) return true;

    IdAssignment false_assignment = assignment;
    false_assignment[var] = false;
    if (dpll(cnf, false_assignment, result)) return true;

    return false;
}

std::string result_json(bool sat, const VarMap& var_map, const IdAssignment& assignment) {
    if (!sat) return "{\"sat\":false,\"assignment\":{}}";

    std::string json = "{\"sat\":true,\"assignment\":{";
    bool first = true;
    for (const auto& kv : var_map) {
        if (!first) json += ",";
        first = false;
        auto it = assignment.find(kv.second);
        bool value = it == assignment.end() ? true : it->second;
        json += "\"" + escape_json(kv.first) + "\":" + (value ? "true" : "false");
    }
    json += "}}";
    return json;
}

std::string read_input(int argc, char* argv[]) {
    auto normalize = [](std::string input) {
        if (input.size() >= 3 &&
            static_cast<unsigned char>(input[0]) == 0xEF &&
            static_cast<unsigned char>(input[1]) == 0xBB &&
            static_cast<unsigned char>(input[2]) == 0xBF) {
            input.erase(0, 3);
        }
        if (input.size() >= 2 &&
            static_cast<unsigned char>(input[0]) == 0xFF &&
            static_cast<unsigned char>(input[1]) == 0xFE) {
            input.erase(0, 2);
        }
        std::string clean;
        clean.reserve(input.size());
        for (char c : input) {
            if (c != '\0') clean += c;
        }
        return clean;
    };

    if (argc > 1) {
        std::string input;
        for (int i = 1; i < argc; ++i) {
            if (i > 1) input += " ";
            input += argv[i];
        }
        return normalize(input);
    }
    std::string input;
    std::string line;
    while (std::getline(std::cin, line)) input += line;
    return normalize(input);
}

}  // namespace

#ifndef DPLL_NO_MAIN
int main(int argc, char* argv[]) {
    try {
        std::string input = read_input(argc, argv);
        if (input.empty()) throw std::runtime_error("Input is empty");

        CNFInput cnf = JsonParser(input).parse();
        IdAssignment solution;
        bool sat = dpll(cnf.clauses, IdAssignment{}, solution);
        std::cout << result_json(sat, cnf.var_map, solution) << '\n';
        return 0;
    } catch (const std::exception& ex) {
        std::cout << error_json(ex.what()) << '\n';
        return 1;
    }
}
#endif
