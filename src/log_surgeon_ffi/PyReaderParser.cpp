#include <wrapped_facade_headers/Python.hpp>

#include "PyReaderParser.hpp"

#include <algorithm>
#include <iostream>
#include <log_surgeon/Constants.hpp>
#include <log_surgeon/Reader.hpp>
#include <log_surgeon/ReaderParser.hpp>
#include <log_surgeon/SchemaParser.hpp>
#include <log_surgeon_ffi/api_decoration.hpp>
#include <log_surgeon_ffi/PyObjectCast.hpp>
#include <log_surgeon_ffi/PyObjectUtils.hpp>
#include <log_surgeon_ffi/utils.hpp>
#include <memory>
#include <span>
#include <string>
#include <tuple>
#include <utility>

namespace log_surgeon_ffi {
namespace {
/**
 * Callback of `PyReaderParser`'s `__init__` method:
 */
// NOLINTNEXTLINE(cppcoreguidelines-avoid-c-arrays)
PyDoc_STRVAR(
        cPyReaderParserDoc,
        "Parser for parsing log events using log-surgeon schemas.\n"
        "This class parses unstructured log messages into structured log events "
        "with extracted variables.\n\n"
        "__init__(self, input_stream, schema_content, group_name_resolver, debug=False)\n\n"
        "Initializes a :class:`ReaderParser` instance with the given inputs.\n\n"
        ":param input_stream: Input stream containing log data.\n"
        ":type input_stream: IO[bytes]\n"
        ":param schema_content: Schema definition string for parsing.\n"
        ":type schema_content: str\n"
        ":param group_name_resolver: Resolver for mapping logical to physical group names.\n"
        ":type group_name_resolver: GroupNameResolver\n"
        ":param debug: Whether to enable debug output to stderr (default: False).\n"
        ":type debug: bool\n"
);
LOG_SURGEON_FFI_METHOD auto
PyReaderParser_init(PyReaderParser* self, PyObject* args, PyObject* keywords) -> int;

/**
 * Callback of `PyReaderParser`'s `reset_input_stream`.
 */
PyDoc_STRVAR(
        cPyReaderParserResetInputStreamDoc,
        "reset_input_stream(self)\n"
        "--\n\n"
        "Deserializes the next log event from the IR stream.\n\n"
        ":return:\n"
        "     - The next deserialized log event from the IR stream.\n"
        "     - None if there are no more log events in the stream.\n"
        ":rtype: :class:`KeyValuePairLogEvent` | None\n"
        ":raises: Appropriate exceptions with detailed information on any "
        "encountered failure.\n"
);
LOG_SURGEON_FFI_METHOD auto
PyReaderParser_reset_input_stream(PyReaderParser* self, PyObject* args, PyObject* keywords)
        -> PyObject*;

/**
 * Callback of `PyReaderParser`'s `done`.
 */
PyDoc_STRVAR(
        cPyReaderParserDoneDoc,
        "done(self)\n"
        "--\n\n"
        "Deserializes the next log event from the IR stream.\n\n"
        ":return:\n"
        "     - The next deserialized log event from the IR stream.\n"
        "     - None if there are no more log events in the stream.\n"
        ":rtype: :class:`KeyValuePairLogEvent` | None\n"
        ":raises: Appropriate exceptions with detailed information on any "
        "encountered failure.\n"
);
LOG_SURGEON_FFI_METHOD auto PyReaderParser_done(PyReaderParser* self) -> PyObject*;

/**
 * Callback of `PyReaderParser`'s `parse_next_log_event`.
 */
PyDoc_STRVAR(
        cPyReaderParserParseNextLogEventDoc,
        "parse_next_log_event(self)\n"
        "--\n\n"
        "Deserializes the next log event from the IR stream.\n\n"
        ":return:\n"
        "     - The next deserialized log event from the IR stream.\n"
        "     - None if there are no more log events in the stream.\n"
        ":rtype: :class:`KeyValuePairLogEvent` | None\n"
        ":raises: Appropriate exceptions with detailed information on any "
        "encountered failure.\n"
);
LOG_SURGEON_FFI_METHOD auto PyReaderParser_parse_next_log_event(PyReaderParser* self) -> PyObject*;

/**
 * Callback of `PyReaderParser`'s deallocator.
 */
LOG_SURGEON_FFI_METHOD auto PyReaderParser_dealloc(PyReaderParser* self) -> void;

// NOLINTNEXTLINE(*-avoid-c-arrays,
// cppcoreguidelines-avoid-non-const-global-variables)
PyMethodDef PyReaderParser_method_table[]{
        {"reset_input_stream",
         py_c_function_cast(PyReaderParser_reset_input_stream),
         METH_VARARGS | METH_KEYWORDS,
         static_cast<char const*>(cPyReaderParserResetInputStreamDoc)},

        {"done",
         py_c_function_cast(PyReaderParser_done),
         METH_NOARGS,
         static_cast<char const*>(cPyReaderParserDoneDoc)},

        {"parse_next_log_event",
         py_c_function_cast(PyReaderParser_parse_next_log_event),
         METH_NOARGS,
         static_cast<char const*>(cPyReaderParserParseNextLogEventDoc)},

        {nullptr}
};

// NOLINTBEGIN(cppcoreguidelines-pro-type-*-cast)
// NOLINTNEXTLINE(*-avoid-c-arrays, cppcoreguidelines-avoid-non-const-global-variables)
PyType_Slot PyReaderParser_slots[]{
        {Py_tp_alloc, reinterpret_cast<void*>(PyType_GenericAlloc)},
        {Py_tp_dealloc, reinterpret_cast<void*>(PyReaderParser_dealloc)},
        {Py_tp_new, reinterpret_cast<void*>(PyType_GenericNew)},
        {Py_tp_init, reinterpret_cast<void*>(PyReaderParser_init)},
        {Py_tp_methods, static_cast<void*>(PyReaderParser_method_table)},
        {Py_tp_doc, const_cast<void*>(static_cast<void const*>(cPyReaderParserDoc))},
        {0, nullptr}
};
// NOLINTEND(cppcoreguidelines-pro-type-*-cast)

/**
 * `PyReaderParser`'s Python type specifications.
 */
// NOLINTNEXTLINE(cppcoreguidelines-avoid-non-const-global-variables)
PyType_Spec PyReaderParser_type_spec{
        "log_surgeon_ffi.ReaderParser",
        sizeof(PyReaderParser),
        0,
        Py_TPFLAGS_DEFAULT,
        static_cast<PyType_Slot*>(PyReaderParser_slots)
};

LOG_SURGEON_FFI_METHOD auto
PyReaderParser_init(PyReaderParser* self, PyObject* args, PyObject* keywords) -> int {
    static char keyword_input_stream[]{"input_stream"};
    static char keyword_schema_str[]{"schema_contents"};
    static char keyword_group_name_resolver[]{"group_name_resolver"};
    static char keyword_debug[]{"debug"};
    static char const* keyword_table[]{
            static_cast<char*>(keyword_input_stream),
            static_cast<char*>(keyword_schema_str),
            static_cast<char*>(keyword_group_name_resolver),
            static_cast<char*>(keyword_debug),
            nullptr
    };

    PyObject* py_input_stream{};
    char const* schema_contents{};
    PyObject* py_group_name_resolver{};
    int debug{0};
    if (false
        == static_cast<bool>(PyArg_ParseTupleAndKeywords(
                args,
                keywords,
                "OsO|p",
                const_cast<char**>(static_cast<char const**>(keyword_table)),
                &py_input_stream,
                &schema_contents,
                &py_group_name_resolver,
                &debug
        )))
    {
        // TODO: do we need to set our own exceptions here?
        return -1;
    }

    if (false == self->init(py_input_stream, schema_contents, py_group_name_resolver, 1 == debug)) {
        // TODO: do we need to set our own exceptions here?
        return -1;
    }

    return 0;
}

LOG_SURGEON_FFI_METHOD auto
PyReaderParser_reset_input_stream(PyReaderParser* self, PyObject* args, PyObject* keywords)
        -> PyObject* {
    static char keyword_input_stream[]{"input_stream"};
    static char const* keyword_table[]{static_cast<char*>(keyword_input_stream), nullptr};

    PyObject* py_input_stream{};
    if (false
        == static_cast<bool>(PyArg_ParseTupleAndKeywords(
                args,
                keywords,
                "O",
                const_cast<char**>(static_cast<char const**>(keyword_table)),
                &py_input_stream
        )))
    {
        return PyBool_FromLong(0);
    }
    return self->reset_input_stream(py_input_stream) ? PyBool_FromLong(1) : PyBool_FromLong(0);
}

LOG_SURGEON_FFI_METHOD auto PyReaderParser_done(PyReaderParser* self) -> PyObject* {
    return self->done() ? PyBool_FromLong(1) : PyBool_FromLong(0);
}

LOG_SURGEON_FFI_METHOD auto PyReaderParser_parse_next_log_event(PyReaderParser* self) -> PyObject* {
    return self->parse_next_log_event();
}

LOG_SURGEON_FFI_METHOD auto PyReaderParser_dealloc(PyReaderParser* self) -> void {
    self->dealloc();
    Py_TYPE(self)->tp_free(py_reinterpret_cast<PyObject>(self));
}

auto get_py_token_array(PyObject* py_var_dict, char const* token_name) -> PyObject* {
    PyObject* py_token_name{PyUnicode_FromString(token_name)};
    if (nullptr == py_token_name) {
        return nullptr;
    }
    PyObject* py_token_array{nullptr};
    auto contains_token_result{PyDict_Contains(py_var_dict, py_token_name)};
    if (-1 == contains_token_result) {
        // TODO: throw
        return nullptr;
    }
    if (1 == contains_token_result) {
        py_token_array = PyDict_GetItem(py_var_dict, py_token_name);
    } else {
        py_token_array = PyList_New(0);
        if (-1 == PyDict_SetItem(py_var_dict, py_token_name, py_token_array)) {
            // TODO: throw
            return nullptr;
        }
    }
    return py_token_array;
}
}  // namespace

auto PyReaderParser::module_level_init(PyObject* py_module) -> bool {
    auto* type{py_reinterpret_cast<PyTypeObject>(PyType_FromSpec(&PyReaderParser_type_spec))};
    m_py_type.reset(type);
    if (nullptr == type) {
        return false;
    }
    return add_python_type(get_py_type(), "ReaderParser", py_module);
}

auto PyReaderParser::init(
        PyObject* py_input_stream,
        char const* schema_content,
        PyObject* py_group_name_resolver,
        bool debug
) -> bool {
    // TODO use try catch + throw a py exception around log surgeon code
    // TODO review PyErr and exceptions on returns

    m_debug = debug;
    m_parser = std::make_unique<log_surgeon::ReaderParser>(
            log_surgeon::SchemaParser::try_schema_string(schema_content)
    );

    // Store the group name resolver and increment its reference count
    m_py_group_name_resolver = py_group_name_resolver;
    Py_INCREF(py_group_name_resolver);

    return reset_input_stream(py_input_stream);

    // TODO: add error handling code?
    //     if (deserializer_result.has_error()) {
    //         PyErr_Format(
    //                 PyExc_RuntimeError,
    //                 get_c_str_from_constexpr_string_view(cDeserializerCreateErrorFormatStr),
    //                 deserializer_result.error().message().c_str()
    //         );
    //         return false;
    //     }
    //     m_deserializer = new (std::nothrow)
    //             clp::ffi::ir_stream::Deserializer<PyReaderParser::IrUnitHandler>{
    //                     std::move(deserializer_result.value())
    //             };
    //     if (nullptr == m_deserializer) {
    //         PyErr_SetString(
    //                 PyExc_RuntimeError,
    //                 get_c_str_from_constexpr_string_view(cOutOfMemoryError)
    //         );
    //         return false;
    //     }
}

auto PyReaderParser::reset_input_stream(PyObject* py_input_stream) -> bool {
    if (0 == PyObject_HasAttrString(py_input_stream, "read")) {
        PyErr_SetString(PyExc_TypeError, "input_stream must have a .read() method");
        return false;
    }

    m_py_input_stream = py_input_stream;
    Py_INCREF(py_input_stream);

    log_surgeon::Reader reader{
            [&](char* buf, size_t count, size_t& read_to) -> log_surgeon::ErrorCode {
                PyObject* py_data{PyObject_CallMethod(
                        m_py_input_stream,
                        "read",
                        "n",
                        static_cast<Py_ssize_t>(count)
                )};
                if (py_data == nullptr) {
                    return log_surgeon::ErrorCode::Errno;
                }

                char* py_buf{};
                Py_ssize_t size{};
                if (PyBytes_Check(py_data)) {
                    if (0 != PyBytes_AsStringAndSize(py_data, &py_buf, &size)) {
                        Py_DECREF(py_data);
                        return log_surgeon::ErrorCode::Errno;
                    }
                } else if (PyUnicode_Check(py_data)) {
                    PyObject* py_bytes{PyUnicode_AsEncodedString(py_data, "utf-8", "strict")};
                    if (nullptr == py_bytes) {
                        Py_DECREF(py_data);
                        return log_surgeon::ErrorCode::Errno;
                    }
                    if (0 != PyBytes_AsStringAndSize(py_bytes, &py_buf, &size)) {
                        Py_DECREF(py_bytes);
                        Py_DECREF(py_data);
                        return log_surgeon::ErrorCode::Errno;
                    }
                    Py_DECREF(py_bytes);
                } else {
                    Py_DECREF(py_data);
                    PyErr_SetString(
                            PyExc_TypeError,
                            "input_stream.read() must return bytes or str"
                    );
                    return log_surgeon::ErrorCode::Errno;
                }
                read_to = static_cast<size_t>(size);

                std::span<char> const py_span{py_buf, read_to};
                std::copy(py_span.begin(), py_span.end(), buf);
                Py_DECREF(py_buf);

                if (0 == read_to) {
                    // PyErr_SetString(
                    //         get_py_incomplete_stream_error(),
                    //         get_c_str_from_constexpr_string_view(cDeserializerIncompleteIRError)
                    // );
                    return log_surgeon::ErrorCode::EndOfFile;
                }

                // TODO: double check what to do if the read was truncated
                // if (read_to < count) {
                //     return log_surgeon::ErrorCode::Truncated;
                // }
                return log_surgeon::ErrorCode::Success;
            }
    };
    m_parser->reset_and_set_reader(reader);
    return true;
}

auto PyReaderParser::dealloc() -> void {
    std::ignore = m_parser.release();
    Py_XDECREF(m_py_group_name_resolver);
}

auto PyReaderParser::done() -> bool {
    return m_parser->done();
}

auto PyReaderParser::parse_next_log_event() -> PyObject* {
    if (done()) {
        return Py_None;
    }

    if (log_surgeon::ErrorCode::Success != m_parser->parse_next_event()) {
        if (m_debug) {
            std::cerr << "log surgeon failed\n";
        }
        // TODO: throw
        return Py_None;
    }

    auto const& log_parser{m_parser->get_log_parser()};
    auto const& event{log_parser.get_log_event_view()};

    PyObject* py_log_event_module = PyImport_ImportModule("log_surgeon.log_event");
    if (nullptr == py_log_event_module) {
        return Py_None;
    }

    PyObject* py_log_event_callable = PyObject_GetAttrString(py_log_event_module, "LogEvent");
    Py_DECREF(py_log_event_module);
    if (nullptr == py_log_event_callable) {
        return Py_None;
    }

    PyObject* py_log_event = PyObject_CallObject(py_log_event_callable, nullptr);
    Py_DECREF(py_log_event_callable);

    PyObject* py_log_msg{PyUnicode_FromString(event.to_string().c_str())};
    if (nullptr == py_log_msg) {
        Py_DECREF(py_log_event);
        return Py_None;
    }

    auto const set_log_msg_result{PyObject_SetAttrString(py_log_event, "_log_message", py_log_msg)};
    Py_DECREF(py_log_msg);
    if (-1 == set_log_msg_result) {
        Py_DECREF(py_log_event);
        return Py_None;
    }

    // Set the group name resolver on the log event
    auto const set_resolver_result{
            PyObject_SetAttrString(py_log_event, "_group_name_resolver", m_py_group_name_resolver)
    };
    if (-1 == set_resolver_result) {
        Py_DECREF(py_log_event);
        return Py_None;
    }

    PyObject* py_var_dict{PyObject_GetAttrString(py_log_event, "_var_dict")};
    if (nullptr == py_var_dict) {
        Py_DECREF(py_log_event);
        Py_DECREF(py_log_msg);
        return Py_None;
    }

    PyObject* py_logtype{PyUnicode_FromString(event.get_logtype().c_str())};
    if (-1 == PyDict_SetItemString(py_var_dict, "@LogType", py_logtype)) {
        // TODO: throw
        return Py_None;
    }

    if (m_debug) {
        std::cerr << "log message: '" << event.to_string() << "'\n";
        std::cerr << "log type: '" << event.get_logtype().c_str() << "'\n";
    }

    auto const& log_buf = event.get_log_output_buffer();
    auto starting_token_idx{log_buf->has_timestamp() ? 0 : 1};
    for (auto token_idx{starting_token_idx}; token_idx < log_buf->pos(); token_idx++) {
        auto token_view{log_buf->get_token(token_idx)};
        if (1 < token_idx || (1 == token_idx && true == log_buf->has_timestamp())) {
            token_view.m_start_pos++;
        }

        auto const token_type{token_view.m_type_ids_ptr->at(0)};
        auto const token_name{log_parser.get_id_symbol(token_type)};
        auto token_str{token_view.to_string()};
        if (m_debug) {
            std::cerr << "token name: " << token_name << " token: '" << token_str << "'\n";
        }

        switch (token_type) {
            case static_cast<int>(log_surgeon::SymbolId::TokenNewline):
            case static_cast<int>(log_surgeon::SymbolId::TokenUncaughtString): {
                break;
            }
            case static_cast<int>(log_surgeon::SymbolId::TokenInt): {
                PyObject* py_token_long{PyLong_FromString(token_str.c_str(), nullptr, 10)};
                if (nullptr == py_token_long) {
                    py_token_long = PyUnicode_FromString(token_str.c_str());
                }
                PyObject* py_token_array{get_py_token_array(py_var_dict, token_name.c_str())};
                if (-1 == PyList_Append(py_token_array, py_token_long)) {
                    // TODO: throw
                    return Py_None;
                }
                break;
            }
            case static_cast<int>(log_surgeon::SymbolId::TokenFloat): {
                PyObject* py_token_float{PyFloat_FromDouble(std::stod(token_str))};
                if (nullptr == py_token_float) {
                    py_token_float = PyUnicode_FromString(token_str.c_str());
                }
                PyObject* py_token_array{get_py_token_array(py_var_dict, token_name.c_str())};
                if (-1 == PyList_Append(py_token_array, py_token_float)) {
                    // TODO: throw
                    return Py_None;
                }
                break;
            }
            default: {
                auto const& lexer{event.get_log_parser().m_lexer};
                auto capture_ids{lexer.get_capture_ids_from_rule_id(token_type)};

                if (false == token_name.starts_with("LogSurgeonHiddenVariables")) {
                    PyObject* py_token_str{PyUnicode_FromString(token_str.c_str())};
                    PyObject* py_token_array{get_py_token_array(py_var_dict, token_name.c_str())};
                    if (-1 == PyList_Append(py_token_array, py_token_str)) {
                        // TODO: throw
                        return Py_None;
                    }
                }
                if (false == capture_ids.has_value()) {
                    break;
                }

                for (auto const capture_id : capture_ids.value()) {
                    auto const register_ids{lexer.get_reg_ids_from_capture_id(capture_id)};
                    if (false == register_ids.has_value()) {
                        // TODO: throw
                        return Py_None;
                    }

                    auto const [start_reg_id, end_reg_id]{register_ids.value()};
                    auto const start_positions{token_view.get_reversed_reg_positions(start_reg_id)};
                    auto const end_positions{token_view.get_reversed_reg_positions(end_reg_id)};

                    auto capture_name{lexer.m_id_symbol.at(capture_id)};
                    PyObject* py_capture_array{
                            get_py_token_array(py_var_dict, capture_name.c_str())
                    };
                    // TODO log surgeon currently does not support multicaptures.
                    if (false == start_positions.empty() && -1 < start_positions[0]
                        && false == end_positions.empty() && -1 < end_positions[0])
                    {
                        auto capture_view{token_view};
                        capture_view.m_start_pos = start_positions[0];
                        capture_view.m_end_pos = end_positions[0];
                        PyObject* py_capture{
                                PyUnicode_FromString(capture_view.to_string().c_str())
                        };
                        if (-1 == PyList_Append(py_capture_array, py_capture)) {
                            // TODO: throw
                            return Py_None;
                        }
                    }
                }
                break;
            }
        }
    }
    return py_log_event;
}
}  // namespace log_surgeon_ffi
