#ifndef LOG_SURGEON_FFI_PYREADERPARSER_HPP
#define LOG_SURGEON_FFI_PYREADERPARSER_HPP

#include <wrapped_facade_headers/Python.hpp>

#include <log_surgeon/ReaderParser.hpp>
#include <log_surgeon_ffi/PyObjectUtils.hpp>
#include <memory>

namespace log_surgeon_ffi {
/**
 * A PyObject structure for deserializing CLP key-value pair IR stream. The
 * underlying deserializer is pointed by `m_deserializer`, which reads the IR
 * stream from a Python `IO[byte]` object via `DeserializerBufferReader`.
 */
class PyReaderParser {
public:
    /**
     * Gets the `PyTypeObject` that represents `PyReaderParser`'s Python type.
     * This type is dynamically created and initialized during the execution of
     * `PyReaderParser::module_level_init`.
     * @return Python type object associated with `PyReaderParser`.
     */
    [[nodiscard]] static auto get_py_type() -> PyTypeObject* { return m_py_type.get(); }

    /**
     * Creates and initializes `PyReaderParser` as a Python type, and then
     * incorporates this type as a Python object into the py_module module.
     * @param py_module This is the Python module where the initialized
     * `PyReaderParser` will be incorporated.
     * @return true on success.
     * @return false on failure with the relevant Python exception and error set.
     */
    [[nodiscard]] static auto module_level_init(PyObject* py_module) -> bool;

    // Delete default constructor to disable direct instantiation.
    PyReaderParser() = delete;

    // Delete copy & move constructors and assignment operators
    PyReaderParser(PyReaderParser const&) = delete;
    PyReaderParser(PyReaderParser&&) = delete;
    auto operator=(PyReaderParser const&) -> PyReaderParser& = delete;
    auto operator=(PyReaderParser&&) -> PyReaderParser& = delete;

    // Destructor
    ~PyReaderParser() = default;

    /**
     * Deallocate/release all memory for Python dealloc.
     */
    auto dealloc() -> void;

    /**
     * Since the memory allocation of `PyReaderParser` is handled by CPython's
     * allocator, cpp constructors will not be explicitly called. This function
     * serves as the default constructor to initialize the underlying parser.
     * Other data members are assumed to be zero-initialized by `default-init`
     * method. It has to be manually called whenever creating a new
     * `PyReaderParser` object through CPython APIs.
     * @param py_input_stream The input stream. Must be a Python `IO[bytes]` object.
     * @param schema_content The schema definition string for parsing.
     * @param py_group_name_resolver GroupNameResolver for mapping logical to physical group names.
     * @param debug Whether to enable debug output to stderr.
     * @return true on success.
     * @return false on failure with the relevant Python exception and error set.
     */
    [[nodiscard]] auto init(PyObject* py_input_stream, char const* schema_content, PyObject* py_group_name_resolver, bool debug) -> bool;

    /**
     * Deserializes the next key value pair log event from the IR stream.
     * @return A new reference to a `KeyValuePairLogEvent` object representing the
     * deserialized log event on success.
     * @return A new reference to `Py_None` when the end of IR stream is reached.
     * @return nullptr on failure with the relevant Python exception and error
     * set.
     */
    [[nodiscard]] auto reset_input_stream(PyObject* py_input_stream) -> bool;

    /**
     * Deserializes the next key value pair log event from the IR stream.
     * @return A new reference to a `KeyValuePairLogEvent` object representing the
     * deserialized log event on success.
     * @return A new reference to `Py_None` when the end of IR stream is reached.
     * @return nullptr on failure with the relevant Python exception and error
     * set.
     */
    [[nodiscard]] auto done() -> bool;

    /**
     * Deserializes the next key value pair log event from the IR stream.
     * @return A new reference to a `KeyValuePairLogEvent` object representing the
     * deserialized log event on success.
     * @return A new reference to `Py_None` when the end of IR stream is reached.
     * @return nullptr on failure with the relevant Python exception and error
     * set.
     */
    [[nodiscard]] auto parse_next_log_event() -> PyObject*;

private:
    static inline PyObjectStaticPtr<PyTypeObject> m_py_type{nullptr};

    PyObject_HEAD;
    bool m_debug{false};
    PyObject* m_py_input_stream{nullptr};
    PyObject* m_py_group_name_resolver{nullptr};
    std::unique_ptr<log_surgeon::ReaderParser> m_parser;
};
}  // namespace log_surgeon_ffi

#endif  // LOG_SURGEON_FFI_PYREADERPARSER_HPP
