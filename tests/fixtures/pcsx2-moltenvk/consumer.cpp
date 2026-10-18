#include "fixture.hpp"
#include <MoltenVK/mvk_private_api.h>
#include <array>
#include <cmath>
#include <cstring>
#include <dlfcn.h>
#include <filesystem>
#include <fstream>

namespace {
void profile(Context& c) {
    Dl_info loaded{};
    require(dladdr(reinterpret_cast<void*>(&vkCreateInstance),&loaded)!=0,"dladdr failed");
    require(std::filesystem::canonical(loaded.dli_fname)==std::filesystem::canonical(SH3_EXPECTED_MVK),"wrong loaded MoltenVK");
    MVKConfiguration config{};size_t size=sizeof config;
    checked(vkGetMoltenVKConfigurationMVK(c.instance,&config,&size),"configuration");
    // The pinned recipe sets CONFIG_USE_METAL_PRIVATE_API=1, but omits the
    // compile-time MVK_USE_METAL_PRIVATE_API switch (default 0). MoltenVK's
    // configuration normalization therefore forces the effective value to 0.
    require(!config.useMetalArgumentBuffers && !config.useMetalPrivateAPI,"effective recipe config differs");
    VkPhysicalDeviceDriverProperties driver{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES};
    VkPhysicalDeviceProperties2 props{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2};props.pNext=&driver;
    vkGetPhysicalDeviceProperties2(c.physical,&props);
    require(driver.driverID==VK_DRIVER_ID_MOLTENVK,"unexpected driver ID");
    static_assert(MVK_VERSION == 10401);
    // MoltenVK uses decimal MjMnPt, not Vulkan's packed API-version format.
    require(props.properties.driverVersion==MVK_VERSION,"wrong driver version");
    require(props.properties.apiVersion>=VK_API_VERSION_1_1,"Vulkan 1.1 required");
    std::cout<<"MoltenVK 1.4.1; device="<<props.properties.deviceName
             <<"; driver="<<driver.driverName<<"; api="<<props.properties.apiVersion
             <<"; argumentBuffers="<<config.useMetalArgumentBuffers<<"; privateAPI="<<config.useMetalPrivateAPI<<'\n';
}

void errors() {
    dlerror();void* absent=dlopen("/nonexistent/sh3-moltenvk-test.dylib",RTLD_NOW);
    require(!absent && dlerror(),"missing dylib should fail");
    const char* missing="VK_SH3_nonexistent_extension";
    VkInstanceCreateInfo bad{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
    bad.enabledExtensionCount=1;bad.ppEnabledExtensionNames=&missing;VkInstance instance{};
    auto result=vkCreateInstance(&bad,nullptr,&instance);
    Cleanup cleanup([&]{if(instance)vkDestroyInstance(instance,nullptr);});
    require(result==VK_ERROR_EXTENSION_NOT_PRESENT,"wrong missing extension result");
    require(!instance,"failed instance returned an object");
    Context recovered;recovered.initialize();
    require(vkGetInstanceProcAddr(recovered.instance,"vkSH3NonexistentFunction")==nullptr,"unknown function should be absent");
    profile(recovered);
}

void transfer(Context& c) {
    constexpr size_t count=256;
    Buffer from(c),to(c);from.create(count*4,VK_BUFFER_USAGE_TRANSFER_SRC_BIT);
    to.create(count*4,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    from.mapped([](void* data){auto p=static_cast<uint32_t*>(data);for(uint32_t i=0;i<count;++i)p[i]=(i*17u)^0xa55a1234u;});
    to.mapped([](void* data){std::memset(data,0,count*4);});
    c.submit([&](VkCommandBuffer cmd){
        barrier(cmd,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_ACCESS_HOST_WRITE_BIT,VK_ACCESS_TRANSFER_READ_BIT|VK_ACCESS_TRANSFER_WRITE_BIT);
        VkBufferCopy region{0,0,count*4};vkCmdCopyBuffer(cmd,from.buffer,to.buffer,1,&region);
        barrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,VK_ACCESS_TRANSFER_WRITE_BIT,VK_ACCESS_HOST_READ_BIT);
    });
    to.mapped([](void* data){auto p=static_cast<uint32_t*>(data);for(uint32_t i=0;i<count;++i)require(p[i]==((i*17u)^0xa55a1234u),"GPU copy differs");});
    std::cout<<"256 transferred words match CPU oracle\n";
}

void compute(Context& c,const char* path) {
    std::ifstream input(path,std::ios::binary|std::ios::ate);require(bool(input),"missing SPIR-V");
    const auto bytes=input.tellg();require(bytes>0 && bytes%4==0,"invalid SPIR-V size");
    std::vector<uint32_t> words(static_cast<size_t>(bytes)/4);input.seekg(0);
    input.read(reinterpret_cast<char*>(words.data()),bytes);require(bool(input),"truncated SPIR-V");
    VkShaderModuleCreateInfo sm{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};sm.codeSize=static_cast<size_t>(bytes);sm.pCode=words.data();
    VkShaderModule shader{};checked(vkCreateShaderModule(c.device,&sm,nullptr,&shader),"shader");
    Cleanup free_shader([&]{vkDestroyShaderModule(c.device,shader,nullptr);});
    VkDescriptorSetLayoutBinding binding{0,VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,1,VK_SHADER_STAGE_COMPUTE_BIT,nullptr};
    VkDescriptorSetLayoutCreateInfo li{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};li.bindingCount=1;li.pBindings=&binding;
    VkDescriptorSetLayout layout{};checked(vkCreateDescriptorSetLayout(c.device,&li,nullptr,&layout),"descriptor layout");
    Cleanup free_layout([&]{vkDestroyDescriptorSetLayout(c.device,layout,nullptr);});
    VkPipelineLayoutCreateInfo pli{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};pli.setLayoutCount=1;pli.pSetLayouts=&layout;
    VkPipelineLayout pipeline_layout{};checked(vkCreatePipelineLayout(c.device,&pli,nullptr,&pipeline_layout),"pipeline layout");
    Cleanup free_pl([&]{vkDestroyPipelineLayout(c.device,pipeline_layout,nullptr);});
    VkComputePipelineCreateInfo pci{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};pci.layout=pipeline_layout;
    pci.stage={VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO};pci.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;pci.stage.module=shader;pci.stage.pName="main";
    VkPipeline pipeline{};checked(vkCreateComputePipelines(c.device,VK_NULL_HANDLE,1,&pci,nullptr,&pipeline),"compute pipeline");
    Cleanup free_pipeline([&]{vkDestroyPipeline(c.device,pipeline,nullptr);});
    VkDescriptorPoolSize pool_size{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,1};
    VkDescriptorPoolCreateInfo dpi{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};dpi.maxSets=1;dpi.poolSizeCount=1;dpi.pPoolSizes=&pool_size;
    VkDescriptorPool pool{};checked(vkCreateDescriptorPool(c.device,&dpi,nullptr,&pool),"descriptor pool");
    Cleanup free_pool([&]{vkDestroyDescriptorPool(c.device,pool,nullptr);});
    VkDescriptorSetAllocateInfo dai{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};dai.descriptorPool=pool;dai.descriptorSetCount=1;dai.pSetLayouts=&layout;
    VkDescriptorSet set{};checked(vkAllocateDescriptorSets(c.device,&dai,&set),"descriptor set");
    Buffer values(c);values.create(256*4,VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    values.mapped([](void* data){auto p=static_cast<uint32_t*>(data);for(uint32_t i=0;i<256;++i)p[i]=i*i;});
    VkDescriptorBufferInfo dbi{values.buffer,0,values.size};VkWriteDescriptorSet write{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
    write.dstSet=set;write.dstBinding=0;write.descriptorCount=1;write.descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;write.pBufferInfo=&dbi;
    vkUpdateDescriptorSets(c.device,1,&write,0,nullptr);
    c.submit([&](VkCommandBuffer cmd){
        barrier(cmd,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_ACCESS_HOST_WRITE_BIT,VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT);
        vkCmdBindPipeline(cmd,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);
        vkCmdBindDescriptorSets(cmd,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline_layout,0,1,&set,0,nullptr);
        vkCmdDispatch(cmd,8,1,1);
        barrier(cmd,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,VK_ACCESS_SHADER_WRITE_BIT,VK_ACCESS_HOST_READ_BIT);
    });
    values.mapped([](void* data){auto p=static_cast<uint32_t*>(data);for(uint32_t i=0;i<256;++i)require(p[i]==i*i*3u+7u,"GPU compute differs");});
    std::cout<<"256 computed words match CPU oracle\n";
}

void image(Context& c) {
    VkImageCreateInfo ii{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};ii.imageType=VK_IMAGE_TYPE_2D;ii.format=VK_FORMAT_R8G8B8A8_UNORM;
    ii.extent={8,8,1};ii.mipLevels=1;ii.arrayLayers=1;ii.samples=VK_SAMPLE_COUNT_1_BIT;ii.tiling=VK_IMAGE_TILING_OPTIMAL;
    ii.usage=VK_IMAGE_USAGE_TRANSFER_SRC_BIT|VK_IMAGE_USAGE_TRANSFER_DST_BIT;ii.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
    VkImage image{};VkDeviceMemory memory{};
    Cleanup free_image([&]{if(image)vkDestroyImage(c.device,image,nullptr);if(memory)vkFreeMemory(c.device,memory,nullptr);});
    checked(vkCreateImage(c.device,&ii,nullptr,&image),"image");
    VkMemoryRequirements req{};vkGetImageMemoryRequirements(c.device,image,&req);
    VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};ai.allocationSize=req.size;
    ai.memoryTypeIndex=c.memory_type(req.memoryTypeBits,VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    checked(vkAllocateMemory(c.device,&ai,nullptr,&memory),"image memory");checked(vkBindImageMemory(c.device,image,memory,0),"bind image");
    Buffer readback(c);readback.create(8*8*4,VK_BUFFER_USAGE_TRANSFER_DST_BIT);
    readback.mapped([](void* p){std::memset(p,0,8*8*4);});
    c.submit([&](VkCommandBuffer cmd){
        VkImageMemoryBarrier ib{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};ib.image=image;
        ib.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;ib.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        ib.subresourceRange={VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
        ib.oldLayout=VK_IMAGE_LAYOUT_UNDEFINED;ib.newLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;ib.dstAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&ib);
        VkClearColorValue color{{0.25f,0.5f,0.75f,1.0f}};
        vkCmdClearColorImage(cmd,image,VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,&color,1,&ib.subresourceRange);
        ib.oldLayout=VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;ib.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        ib.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;ib.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&ib);
        VkBufferImageCopy region{};region.imageSubresource={VK_IMAGE_ASPECT_COLOR_BIT,0,0,1};region.imageExtent={8,8,1};
        vkCmdCopyImageToBuffer(cmd,image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,readback.buffer,1,&region);
        barrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,VK_PIPELINE_STAGE_HOST_BIT,VK_ACCESS_TRANSFER_WRITE_BIT,VK_ACCESS_HOST_READ_BIT);
    });
    readback.mapped([](void* data){
        auto p=static_cast<uint8_t*>(data);constexpr std::array<int,4> expected{64,128,191,255};
        for(size_t pixel=0;pixel<64;++pixel)for(size_t ch=0;ch<4;++ch)
            require(std::abs(int(p[pixel*4+ch])-expected[ch])<=(ch==3?0:1),"GPU image readback differs");
    });
    std::cout<<"64 RGBA pixels match clear-color oracle (RGB +/-1, alpha exact)\n";
}
}

int main(int argc,char** argv){
    try{
        require(argc==3,"usage: consumer case shader.spv");std::string name=argv[1];
        if(name=="errors")errors();
        else{Context context;context.initialize();
            if(name=="profile")profile(context);
            else if(name=="transfer")transfer(context);
            else if(name=="compute")compute(context,argv[2]);
            else if(name=="image")image(context);
            else throw std::runtime_error("unknown case");}
        std::cout<<name<<" passed\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
