#include <wrapped_facade_headers/Python.hpp>

#include "PyReaderParser.hpp"

namespace {
// NOLINTBEGIN(cppcoreguidelines-avoid-non-const-global-variables)
// NOLINTNEXTLINE(cppcoreguidelines-avoid-c-arrays, modernize-avoid-c-arrays)
PyMethodDef Py_method_table[]{{nullptr, nullptr, 0, nullptr}};

PyModuleDef Py_log_surgeon_ffi{
        PyModuleDef_HEAD_INIT,
        "log_surgeon_ffi",
        "Python interface to log-surgeon.",
        -1,
        static_cast<PyMethodDef*>(Py_method_table)
};

// NOLINTEND(cppcoreguidelines-avoid-non-const-global-variables)
}  // namespace

// NOLINTNEXTLINE(modernize-use-trailing-return-type)
PyMODINIT_FUNC PyInit_log_surgeon_ffi() {
    PyObject* new_module{PyModule_Create(&Py_log_surgeon_ffi)};
    if (nullptr == new_module) {
        return nullptr;
    }

    if (false == log_surgeon_ffi::PyReaderParser::module_level_init(new_module)) {
        Py_DECREF(new_module);
        return nullptr;
    }

    return new_module;
}
