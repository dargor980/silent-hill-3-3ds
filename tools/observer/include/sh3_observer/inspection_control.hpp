#pragma once
namespace sh3::observer {
enum class InspectionStep { preparation, file_open, file_identity, file_read, digest, images, origin };
class InspectionControl {
public:
  virtual ~InspectionControl() = default;
  // Borrowed, single worker. False must invalidate the owning adapter permanently.
  virtual bool checkpoint(InspectionStep) noexcept = 0;
};
inline bool inspect_continue(InspectionControl* control, InspectionStep step) noexcept {
  return !control || control->checkpoint(step);
}
} // namespace sh3::observer
