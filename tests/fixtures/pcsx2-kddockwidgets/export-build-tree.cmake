# Test plumbing: export the provider's existing target without changing its source.
# Inject with CMAKE_PROJECT_KDDockWidgets_INCLUDE when configuring the provider.
cmake_language(DEFER CALL export EXPORT kddockwidgetsTargets
  FILE "${CMAKE_BINARY_DIR}/src/KDDockWidgets-qt6Targets.cmake" NAMESPACE KDAB::)
