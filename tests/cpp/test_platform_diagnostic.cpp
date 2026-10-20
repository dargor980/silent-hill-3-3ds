#include "sh3_observer/platform_diagnostic.hpp"
#include "check.hpp"
#include <algorithm>
#include <fstream>
#include <limits>
#include <string>
#include <vector>

using namespace sh3::observer;
namespace {
constexpr auto maximum = std::numeric_limits<std::uint64_t>::max();
struct Fixture {
  DiagnosticExpectation expectation;
  DiagnosticRequest request;
  PlatformInventoryResult inventory;
  AdmissionProfile facts{};
  DiagnosticEpochs epochs{11,12,13,14};
  DiagnosticBytes bytes{};
  Fixture() {
    expectation.profile = IdentityProfile::macos_platform_slices_v2;
    expectation.policy_evidence.fill(3); expectation.application_evidence.fill(4);
    expectation.platform_evidence.fill(5);
    for (std::size_t i = 0; i < 16; ++i) {
      request.challenge[i] = i + 1; inventory.process.nonce[i] = i + 17;
    }
    request.sequence = 0x0102030405060708;
    inventory.profile = expectation.profile; inventory.scope = IdentityScope::application_headers;
    inventory.platform_assumed = true; inventory.process.pid = 0x12345678;
    inventory.process.birth_ns = 0x1020304050607080;
    inventory.file_objects.fill(1); inventory.classified_images.fill(2);
    inventory.policy_evidence = expectation.policy_evidence;
    inventory.application_evidence = expectation.application_evidence;
    inventory.platform_evidence = expectation.platform_evidence;
    inventory.loader_revision = 0x0807060504030201;
    inventory.application_images = 26; inventory.platform_images = 621;
    for (std::size_t i = 0; i < facts.size(); ++i) facts[i] = static_cast<AdmissionFact>(i % 3);
  }
  bool encode() { return encode_platform_diagnostic(expectation,request,inventory,facts,epochs,bytes); }
  void rejected() { bytes.fill(255); CHECK(!encode()); CHECK(std::all_of(bytes.begin(),bytes.end(),[](auto b){return b==0;})); }
};
std::vector<std::uint8_t> vector(const std::string& path) {
  std::ifstream file(path); CHECK(file.good()); std::string hex; file >> hex;
  CHECK(hex.size() % 2 == 0); std::vector<std::uint8_t> out;
  for (std::size_t i = 0; i < hex.size(); i += 2) out.push_back(std::stoul(hex.substr(i,2),nullptr,16));
  return out;
}
void failed_request(const std::uint8_t* data, std::size_t size) {
  DiagnosticRequest request; request.challenge.fill(7); request.sequence = 9;
  CHECK(!decode_diagnostic_request(data,size,request)); CHECK(request.sequence == 0);
  CHECK(std::all_of(request.challenge.begin(),request.challenge.end(),[](auto b){return b==0;}));
}
}
int main(int argc, char** argv) {
  CHECK(argc == 3); const std::string mode = argv[1], root = argv[2];
  Fixture f;
  if (mode == "vector") {
    CHECK(f.encode()); const auto expected = vector(root+"/observed.hex");
    CHECK(expected.size() == f.bytes.size()); CHECK(std::equal(expected.begin(),expected.end(),f.bytes.begin()));
    CHECK(encode_diagnostic_rejection(f.request,DiagnosticRejection::cancelled,f.bytes));
    const auto rejected = vector(root+"/rejected.hex"); CHECK(std::equal(rejected.begin(),rejected.end(),f.bytes.begin()));
  } else if (mode == "request") {
    auto bytes = vector(root+"/request.hex"); DiagnosticRequest request;
    CHECK(decode_diagnostic_request(bytes.data(),bytes.size(),request));
    CHECK(request.sequence == f.request.sequence && request.challenge == f.request.challenge);
    auto legacy = bytes; legacy[7] = '1'; failed_request(legacy.data(),legacy.size());
    for (std::size_t n = 0; n < bytes.size(); ++n) failed_request(bytes.data(),n);
    failed_request(nullptr,bytes.size()); bytes.push_back(0); failed_request(bytes.data(),bytes.size()); bytes.pop_back();
    for (std::size_t i = 0; i < 8; ++i) { bytes[i] ^= 1; failed_request(bytes.data(),bytes.size()); bytes[i] ^= 1; }
    std::fill(bytes.begin()+8,bytes.begin()+24,0); failed_request(bytes.data(),bytes.size());
    bytes = vector(root+"/request.hex");
    for (const auto b : {0,255}) { std::fill(bytes.begin()+24,bytes.end(),b); failed_request(bytes.data(),bytes.size()); }
    bytes[24] = 254; CHECK(decode_diagnostic_request(bytes.data(),bytes.size(),request)); CHECK(request.sequence == maximum-1);
  } else if (mode == "configuration") {
    for (const auto profile : {IdentityProfile::unknown,IdentityProfile::macos_platform_v1,static_cast<IdentityProfile>(255)}) {
      Fixture t; t.expectation.profile = profile; CHECK(!valid_diagnostic_expectation(t.expectation)); t.rejected();
    }
    for (int i = 0; i < 3; ++i) {
      Fixture t; auto* field = i == 0 ? &t.expectation.policy_evidence : i == 1 ? &t.expectation.application_evidence : &t.expectation.platform_evidence;
      field->fill(0); t.rejected();
    }
    f.request.challenge = {}; f.rejected(); f = Fixture{}; f.request.sequence = 0; f.rejected();
    f.request.sequence = maximum; f.rejected();
  } else if (mode == "identity") {
    for (int field = 0; field < 12; ++field) {
      Fixture t;
      switch(field) {
        case 0: t.inventory.failure = PlatformInventoryFailure::lost; break;
        case 1: t.inventory.profile = IdentityProfile::macos_platform_v1; break;
        case 2: t.inventory.scope = IdentityScope::unknown; break;
        case 3: t.inventory.platform_assumed = false; break;
        case 4: t.inventory.process.pid = 0; break;
        case 5: t.inventory.process.pid = 0x80000000; break;
        case 6: t.inventory.process.birth_ns = 0; break;
        case 7: t.inventory.process.nonce = {}; break;
        case 8: t.inventory.file_objects = {}; break;
        case 9: t.inventory.classified_images = {}; break;
        case 10: t.inventory.loader_revision = 0; break;
        case 11: t.inventory.loader_revision = maximum; break;
      }
      t.rejected();
    }
    f.inventory.process.pid = 0x7fffffff; f.inventory.process.birth_ns = maximum;
    f.inventory.loader_revision = maximum-1; f.request.sequence = maximum-1; CHECK(f.encode());
  } else if (mode == "evidence") {
    for (int i = 0; i < 3; ++i) {
      Fixture t; auto* field = i == 0 ? &t.inventory.policy_evidence : i == 1 ? &t.inventory.application_evidence : &t.inventory.platform_evidence;
      field->fill(6); t.rejected(); field->fill(0); t.rejected();
    }
  } else if (mode == "counts") {
    for (const auto counts : {std::pair<std::size_t,std::size_t>{0,1},{2049,0},{1,2048},{26,std::numeric_limits<std::size_t>::max()}}) {
      Fixture t; t.inventory.application_images = counts.first; t.inventory.platform_images = counts.second; t.rejected();
    }
    f.inventory.application_images = 2048; f.inventory.platform_images = 0; CHECK(f.encode());
    f.inventory.application_images = 1; f.inventory.platform_images = 2047; CHECK(f.encode());
    for (const auto counts : {std::pair<std::size_t,std::size_t>{1,1024},{43,1026},{1,2047},{2048,0}}) {
      f.inventory.application_images=counts.first; f.inventory.platform_images=counts.second; CHECK(f.encode());
      const auto expected=vector(root+"/counts-"+std::to_string(counts.first)+"-"+std::to_string(counts.second)+".hex");
      CHECK(expected.size()==f.bytes.size() && std::equal(expected.begin(),expected.end(),f.bytes.begin()));
    }
  } else if (mode == "epochs") {
    for (int i = 0; i < 4; ++i) for (const auto value : {std::uint64_t{0},maximum}) {
      Fixture t; auto* field = i == 0 ? &t.epochs.host : i == 1 ? &t.epochs.pine : i == 2 ? &t.epochs.vu : &t.epochs.gs;
      *field = value; t.rejected();
    }
    f.epochs = {}; f.rejected(); f.facts.fill(AdmissionFact::unknown); CHECK(f.encode());
    CHECK(std::all_of(f.bytes.begin()+244,f.bytes.end(),[](auto b){return b==0;}));
    for (std::size_t i = 0; i < f.facts.size(); ++i) {
      f.facts[i] = AdmissionFact::satisfied; f.rejected(); f.facts[i] = AdmissionFact::unknown;
    }
    f.epochs = {maximum-1,maximum-1,maximum-1,maximum-1}; CHECK(f.encode());
  } else if (mode == "facts") {
    for (int value = 0; value <= 255; ++value) {
      f.facts.fill(static_cast<AdmissionFact>(value)); CHECK(f.encode());
      const auto normalized = value == 1 || value == 2 ? value : 0;
      CHECK(std::all_of(f.bytes.begin()+244,f.bytes.begin()+262,[&](auto b){return b==normalized;}));
    }
    f.epochs = {}; f.facts.fill(static_cast<AdmissionFact>(255)); CHECK(f.encode());
  } else if (mode == "rejection") {
    for (int reason = 0; reason <= 255; ++reason) {
      f.bytes.fill(255); const auto ok = encode_diagnostic_rejection(f.request,static_cast<DiagnosticRejection>(reason),f.bytes);
      CHECK(ok == (reason >= 1 && reason <= 9));
      if (ok) { CHECK(f.bytes[8] == 2 && f.bytes[12] == reason); CHECK(std::all_of(f.bytes.begin()+40,f.bytes.end(),[](auto b){return b==0;})); }
      else CHECK(std::all_of(f.bytes.begin(),f.bytes.end(),[](auto b){return b==0;}));
    }
    f.request.sequence = 0; CHECK(!encode_diagnostic_rejection(f.request,DiagnosticRejection::protocol,f.bytes));
    CHECK(std::all_of(f.bytes.begin(),f.bytes.end(),[](auto b){return b==0;}));
  } else CHECK(false);
}
