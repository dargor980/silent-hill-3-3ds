#pragma once
#include <vulkan/vulkan.h>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

inline void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
inline void checked(VkResult result, const char* operation) {
    if (result != VK_SUCCESS) throw std::runtime_error(std::string(operation)+": "+std::to_string(result));
}
struct Cleanup {
    std::function<void()> action;
    explicit Cleanup(std::function<void()> fn): action(std::move(fn)) {}
    Cleanup(const Cleanup&) = delete;
    ~Cleanup() { action(); }
};

struct Context {
    VkInstance instance{};
    VkPhysicalDevice physical{};
    VkDevice device{};
    VkQueue queue{};
    uint32_t family{};
    VkCommandPool pool{};
    Context() = default;
    Context(const Context&) = delete;
    ~Context() {
        if (pool) vkDestroyCommandPool(device, pool, nullptr);
        if (device) vkDestroyDevice(device, nullptr);
        if (instance) vkDestroyInstance(instance, nullptr);
    }
    void initialize() {
        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
        app.pApplicationName="SH3 synthetic host validation"; app.apiVersion=VK_API_VERSION_1_1;
        const char* portability="VK_KHR_portability_enumeration";
        VkInstanceCreateInfo info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
        info.pApplicationInfo=&app;
        // Portability enumeration belongs to the Vulkan loader. Direct MoltenVK
        // linkage does not advertise it; only enable advertised extensions.
        uint32_t extension_count=0;
        checked(vkEnumerateInstanceExtensionProperties(nullptr,&extension_count,nullptr),"instance extension count");
        std::vector<VkExtensionProperties> extensions(extension_count);
        checked(vkEnumerateInstanceExtensionProperties(nullptr,&extension_count,extensions.data()),"instance extensions");
        for(const auto& ext:extensions) if(std::strcmp(ext.extensionName,portability)==0){
            info.flags=VK_INSTANCE_CREATE_ENUMERATE_PORTABILITY_BIT_KHR;
            info.enabledExtensionCount=1;info.ppEnabledExtensionNames=&portability;
        }
        checked(vkCreateInstance(&info,nullptr,&instance),"instance");
        uint32_t count=0; checked(vkEnumeratePhysicalDevices(instance,&count,nullptr),"physical count");
        require(count>0,"no Metal-backed Vulkan device");
        std::vector<VkPhysicalDevice> devices(count);
        checked(vkEnumeratePhysicalDevices(instance,&count,devices.data()),"physical devices");
        physical=devices.front();
        vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,nullptr);
        std::vector<VkQueueFamilyProperties> families(count);
        vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,families.data());
        bool found=false;
        for (uint32_t i=0;i<count;++i) if (families[i].queueCount && (families[i].queueFlags&VK_QUEUE_COMPUTE_BIT)) {family=i;found=true;break;}
        require(found,"no compute queue");
        float priority=1;
        VkDeviceQueueCreateInfo qi{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
        qi.queueFamilyIndex=family;qi.queueCount=1;qi.pQueuePriorities=&priority;
        VkDeviceCreateInfo di{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
        di.queueCreateInfoCount=1;di.pQueueCreateInfos=&qi;
        const char* subset="VK_KHR_portability_subset";
        di.enabledExtensionCount=1;di.ppEnabledExtensionNames=&subset;
        checked(vkCreateDevice(physical,&di,nullptr,&device),"device");
        vkGetDeviceQueue(device,family,0,&queue);
        VkCommandPoolCreateInfo pi{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};pi.queueFamilyIndex=family;
        checked(vkCreateCommandPool(device,&pi,nullptr,&pool),"pool");
    }
    uint32_t memory_type(uint32_t bits,VkMemoryPropertyFlags flags) const {
        VkPhysicalDeviceMemoryProperties props{};vkGetPhysicalDeviceMemoryProperties(physical,&props);
        for(uint32_t i=0;i<props.memoryTypeCount;++i)
            if((bits&(1u<<i)) && (props.memoryTypes[i].propertyFlags&flags)==flags) return i;
        throw std::runtime_error("no compatible memory type");
    }
    void submit(const std::function<void(VkCommandBuffer)>& record) const {
        VkCommandBufferAllocateInfo ai{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        ai.commandPool=pool;ai.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ai.commandBufferCount=1;
        VkCommandBuffer cmd{};checked(vkAllocateCommandBuffers(device,&ai,&cmd),"command buffer");
        Cleanup free_cmd([&]{vkFreeCommandBuffers(device,pool,1,&cmd);});
        VkCommandBufferBeginInfo bi{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        bi.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        checked(vkBeginCommandBuffer(cmd,&bi),"begin");record(cmd);checked(vkEndCommandBuffer(cmd),"end");
        VkFenceCreateInfo fi{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};VkFence fence{};
        checked(vkCreateFence(device,&fi,nullptr,&fence),"fence");
        Cleanup free_fence([&]{vkDestroyFence(device,fence,nullptr);});
        VkSubmitInfo si{VK_STRUCTURE_TYPE_SUBMIT_INFO};si.commandBufferCount=1;si.pCommandBuffers=&cmd;
        checked(vkQueueSubmit(queue,1,&si,fence),"submit");
        auto result=vkWaitForFences(device,1,&fence,VK_TRUE,5'000'000'000ull);
        // Never free resources still owned by an outstanding GPU submission.
        if(result!=VK_SUCCESS){std::cerr<<"GPU completion failed: "<<result<<std::endl;std::_Exit(3);}
    }
};

struct Buffer {
    Context& context;VkBuffer buffer{};VkDeviceMemory memory{};VkDeviceSize size{};
    explicit Buffer(Context& c):context(c){}
    Buffer(const Buffer&)=delete;
    ~Buffer(){if(buffer)vkDestroyBuffer(context.device,buffer,nullptr);if(memory)vkFreeMemory(context.device,memory,nullptr);}
    void create(VkDeviceSize bytes,VkBufferUsageFlags usage){
        size=bytes;VkBufferCreateInfo bi{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        bi.size=bytes;bi.usage=usage;bi.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
        checked(vkCreateBuffer(context.device,&bi,nullptr,&buffer),"buffer");
        VkMemoryRequirements req{};vkGetBufferMemoryRequirements(context.device,buffer,&req);
        VkMemoryAllocateInfo ai{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};ai.allocationSize=req.size;
        ai.memoryTypeIndex=context.memory_type(req.memoryTypeBits,VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        checked(vkAllocateMemory(context.device,&ai,nullptr,&memory),"memory");
        checked(vkBindBufferMemory(context.device,buffer,memory,0),"bind buffer");
    }
    void mapped(const std::function<void(void*)>& operation){
        void* data=nullptr;checked(vkMapMemory(context.device,memory,0,size,0,&data),"map");
        Cleanup unmap([&]{vkUnmapMemory(context.device,memory);});operation(data);
    }
};

inline void barrier(VkCommandBuffer cmd,VkPipelineStageFlags source,VkPipelineStageFlags dest,
                    VkAccessFlags src_access,VkAccessFlags dst_access){
    VkMemoryBarrier mb{VK_STRUCTURE_TYPE_MEMORY_BARRIER};mb.srcAccessMask=src_access;mb.dstAccessMask=dst_access;
    vkCmdPipelineBarrier(cmd,source,dest,0,1,&mb,0,nullptr,0,nullptr);
}
