#include "memory_files.hpp"
#include "sh3/application/options_store.hpp"
#include <limits>

namespace {
using Store = sh3::application::OptionsStore;
using E = MemoryFiles::E;
using Id = MemoryFiles::Id;

void initialization_and_selection() {
    MemoryFiles files;
    Store store(files, files);
    CHECK(store.save({false}) == E::read_failed); // load must establish the baseline
    CHECK(store.load() == E::missing);
    CHECK(store.current().tone_enabled && store.generation() == 0 && files.writes == 0);
    CHECK(store.save({false}) == E::ok);
    CHECK(!store.current().tone_enabled && store.generation() == 1 &&
          files.last_write == Id::options_a);
    const auto original = files.files[1].bytes;
    CHECK(store.save({}) == E::ok);
    CHECK(store.current().tone_enabled && store.generation() == 2 &&
          files.last_write == Id::options_b);
    CHECK(files.files[1].bytes == original);
    Store reopened(files, files);
    CHECK(reopened.load() == E::ok && reopened.generation() == 2 &&
          reopened.current().tone_enabled);
    CHECK(reopened.save({false}) == E::ok && files.last_write == Id::options_a);
    CHECK(reopened.load() == E::ok && reopened.generation() == 3);
    files.record(Id::options_b, false, 3);
    CHECK(reopened.load() == E::ok); // identical equal-generation records
    files.record(Id::options_b, true, 3);
    CHECK(reopened.load() == E::ambiguous);
    const auto count = files.writes;
    CHECK(reopened.save({}) == E::ambiguous && files.writes == count);
    CHECK(!reopened.current().tone_enabled); // last known in-memory state retained
}

void recovery_and_uncertainty() {
    for (auto error : {E::missing, E::invalid_data, E::too_large}) {
        for (unsigned bad : {1U, 2U}) {
            MemoryFiles files;
            files.record(bad == 1 ? Id::options_b : Id::options_a, false, 9);
            files.files[bad].error = error;
            Store store(files, files);
            CHECK(store.load() == (error == E::missing ? E::ok : error));
            CHECK(store.generation() == 9 && !store.current().tone_enabled);
            CHECK(store.save({}) == E::ok);
            CHECK(static_cast<unsigned>(files.last_write) == bad);
        }
    }
    for (auto error : {E::read_failed, E::permission_denied, E::close_failed}) {
        for (unsigned bad : {1U, 2U}) {
            MemoryFiles files;
            files.record(Id::options_a, false, 5);
            files.record(Id::options_b, true, 6);
            files.files[bad].error = error;
            Store store(files, files);
            CHECK(store.load() == error);
            CHECK(store.save({false}) == error && files.writes == 0);
        }
    }
    MemoryFiles files;
    files.record(Id::options_a, false, 1);
    files.files[1].size = 8; // truncated record, successful raw read
    files.record(Id::options_b, true, 2);
    files.files[2].bytes[12] ^= 1; // checksum
    Store store(files, files);
    CHECK(store.load() == E::invalid_data && store.generation() == 0);
    CHECK(store.save({}) == E::ok && files.last_write == Id::options_a);
    files.record(Id::options_b, false, std::numeric_limits<std::uint32_t>::max());
    CHECK(store.load() == E::ok);
    CHECK(store.save({}) == E::generation_exhausted);
}

void failed_writes_preserve_previous() {
    for (auto error :
         {E::no_space, E::permission_denied, E::write_failed, E::flush_failed, E::close_failed}) {
        MemoryFiles files;
        files.record(Id::options_a, false, 7);
        const auto previous = files.files[1].bytes;
        Store store(files, files);
        CHECK(store.load() == E::ok);
        files.write_error = error;
        CHECK(store.save({}) == error);
        CHECK(store.generation() == 7 && !store.current().tone_enabled);
        CHECK(files.files[1].bytes == previous && files.last_write == Id::options_b);
        files.write_error = E::ok;
        Store reopened(files, files);
        CHECK(reopened.load() == E::invalid_data && reopened.generation() == 7);
    }
    for (auto error : {E::read_failed, E::missing, E::close_failed}) {
        MemoryFiles files;
        files.record(Id::options_b, false, 3);
        Store store(files, files);
        CHECK(store.load() == E::ok);
        files.verify_error = error;
        CHECK(store.save({}) == error && store.generation() == 3);
        CHECK(!store.current().tone_enabled && files.last_write == Id::options_a);
    }
    MemoryFiles files;
    Store store(files, files);
    CHECK(store.load() == E::missing);
    files.corrupt_write = true;
    CHECK(store.save({false}) == E::verify_failed && store.generation() == 0);
    CHECK(store.current().tone_enabled);
    files.corrupt_write = false;
    files.short_verify = true;
    CHECK(store.save({false}) == E::verify_failed && store.generation() == 0);
}
} // namespace
int main() {
    initialization_and_selection();
    recovery_and_uncertainty();
    failed_writes_preserve_previous();
}
