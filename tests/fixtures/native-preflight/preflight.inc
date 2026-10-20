// Diagnostic-only replacement in a verified private source copy (PF01-PF06).
bool preflight() noexcept {
  std::size_t length{};
  std::uintptr_t base{}, address{};
  ImageSnapshot first{}, last{};
  mach_header_64 header{};
  mach_vm_size_t got{};
  kern_return_t status = KERN_SUCCESS;
  const auto reject = [&](const char* reason) noexcept {
    std::fprintf(stderr,
      "SH3_PREFLIGHT_FAIL reason=%s address=%llx base=%llx size=%llu first_count=%zu last_count=%zu first_revision=%llu last_revision=%llu status=%d got=%llu magic=%x flags=%x\n",
      reason, static_cast<unsigned long long>(address), static_cast<unsigned long long>(base),
      static_cast<unsigned long long>(length), first.count, last.count,
      static_cast<unsigned long long>(first.revision), static_cast<unsigned long long>(last.revision),
      status, static_cast<unsigned long long>(got), header.magic, header.flags);
    return false;
  };
  const auto range = symbol<const void*(*)(std::size_t*)>("_dyld_get_shared_cache_range");
  if (!range) return reject("range_api");
  base = reinterpret_cast<std::uintptr_t>(range(&length));
  if (!base || !length || length > UINT64_MAX-base) return reject("range_invalid");
  if (!MacOSImageEvents::read(first)) return reject("first_read");
  if (!normalize(first)) return reject("first_invalid");
  for (std::size_t i=0;i<first.count;++i) {
    header = {}; got = {}; address = first.addresses[i];
    status = mach_vm_read_overwrite(mach_task_self(),address,sizeof(header),reinterpret_cast<mach_vm_address_t>(&header),&got);
    if (status != KERN_SUCCESS) return reject("header_read");
    if (got != sizeof(header)) return reject("header_short");
    if (header.magic != MH_MAGIC_64) return reject("header_magic");
    if ((header.flags&MH_DYLIB_IN_CACHE) && (address < base || address-base >= length))
      return reject("cache_flag_outside");
  }
  if (!MacOSImageEvents::read(last)) return reject("last_read");
  if (!normalize(last)) return reject("last_invalid");
  if (first.count != last.count) return reject("count_changed");
  if (first.revision != last.revision) return reject("revision_changed");
  if (!std::equal(first.addresses.begin(),first.addresses.begin()+first.count,last.addresses.begin()))
    return reject("addresses_changed");
  return true;
}
