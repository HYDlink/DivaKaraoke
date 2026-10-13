#pragma once
#include <d3d11.h>
#include <d3dcompiler.h>
#include <cstring>

// 先在透明纹理中合成一整行，再对合成结果应用一次透明度，避免粗描边叠黑。
class KtvCompositeLayer {
    ID3D11Device* device = nullptr;
    ID3D11Texture2D* texture = nullptr;
    ID3D11RenderTargetView* target = nullptr;
    ID3D11ShaderResourceView* view = nullptr;
    ID3D11VertexShader* vertexShader = nullptr;
    ID3D11PixelShader* pixelShader = nullptr;
    ID3D11Buffer* opacityBuffer = nullptr;
    ID3D11BlendState* blend = nullptr;
    ID3D11RenderTargetView* savedTargets[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT] = {};
    ID3D11DepthStencilView* savedDepth = nullptr;
    UINT width = 0, height = 0;
    bool active = false;

    // 释放一个可为空的 COM 对象并清空指针。
    template<class T> static void Release(T*& object) {
        if (object) object->Release();
        object = nullptr;
    }

    // 清理分辨率相关的临时纹理。
    void ReleaseTexture() {
        Release(view);
        Release(target);
        Release(texture);
        width = height = 0;
    }

    // 清理设备资源，允许设备更换后重新创建。
    void ReleaseResources() {
        ReleaseTexture();
        Release(vertexShader);
        Release(pixelShader);
        Release(opacityBuffer);
        Release(blend);
        Release(device);
    }

    // 编译整体透明合成的着色器，颜色和透明度都按预乘方式缩放。
    bool CreateShaders() {
        const char* source =
            "cbuffer Opacity : register(b0) { float opacity; float3 padding; };"
            "Texture2D layer : register(t0);"
            "float4 VS(uint id : SV_VertexID) : SV_POSITION {"
            "float2 uv = float2((id << 1) & 2, id & 2);"
            "return float4(uv * float2(2, -2) + float2(-1, 1), 0, 1); }"
            "float4 PS(float4 position : SV_POSITION) : SV_Target {"
            "return layer.Load(int3(int2(position.xy), 0)) * opacity; }";
        ID3DBlob* code = nullptr;
        HRESULT result = D3DCompile(source, strlen(source), nullptr, nullptr, nullptr,
            "VS", "vs_4_0", 0, 0, &code, nullptr);
        if (SUCCEEDED(result))
            result = device->CreateVertexShader(code->GetBufferPointer(), code->GetBufferSize(), nullptr, &vertexShader);
        Release(code);
        if (FAILED(result)) return false;
        result = D3DCompile(source, strlen(source), nullptr, nullptr, nullptr,
            "PS", "ps_4_0", 0, 0, &code, nullptr);
        if (SUCCEEDED(result))
            result = device->CreatePixelShader(code->GetBufferPointer(), code->GetBufferSize(), nullptr, &pixelShader);
        Release(code);
        if (FAILED(result)) return false;
        D3D11_BUFFER_DESC buffer = {};
        buffer.ByteWidth = 16;
        buffer.Usage = D3D11_USAGE_DYNAMIC;
        buffer.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
        buffer.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
        if (FAILED(device->CreateBuffer(&buffer, nullptr, &opacityBuffer))) return false;
        D3D11_BLEND_DESC description = {};
        auto& output = description.RenderTarget[0];
        output.BlendEnable = TRUE;
        output.SrcBlend = D3D11_BLEND_ONE;
        output.DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
        output.BlendOp = D3D11_BLEND_OP_ADD;
        output.SrcBlendAlpha = D3D11_BLEND_ONE;
        output.DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
        output.BlendOpAlpha = D3D11_BLEND_OP_ADD;
        output.RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
        return SUCCEEDED(device->CreateBlendState(&description, &blend));
    }

public:
    // 释放临时资源；不持有游戏纹理或游戏生命周期对象。
    ~KtvCompositeLayer() { ReleaseResources(); }

    // 切换到与当前 ImGui 视口一致的透明画布，文字层继续以正常颜色绘制。
    bool Begin(ID3D11Device* newDevice, ID3D11DeviceContext* context) {
        if (!newDevice || !context || active) return false;
        if (device != newDevice || !blend) {
            ReleaseResources();
            device = newDevice;
            device->AddRef();
            if (!CreateShaders()) { ReleaseResources(); return false; }
        }
        D3D11_VIEWPORT viewport = {};
        UINT count = 1;
        context->RSGetViewports(&count, &viewport);
        const UINT newWidth = (UINT)(viewport.TopLeftX + viewport.Width);
        const UINT newHeight = (UINT)(viewport.TopLeftY + viewport.Height);
        if (!count || !newWidth || !newHeight) return false;
        if (!texture || newWidth != width || newHeight != height) {
            ReleaseTexture();
            D3D11_TEXTURE2D_DESC description = {};
            description.Width = newWidth;
            description.Height = newHeight;
            description.MipLevels = description.ArraySize = description.SampleDesc.Count = 1;
            description.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
            description.BindFlags = D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;
            if (FAILED(device->CreateTexture2D(&description, nullptr, &texture)) ||
                FAILED(device->CreateRenderTargetView(texture, nullptr, &target)) ||
                FAILED(device->CreateShaderResourceView(texture, nullptr, &view))) {
                ReleaseTexture();
                return false;
            }
            width = newWidth;
            height = newHeight;
        }
        context->OMGetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT, savedTargets, &savedDepth);
        context->OMSetRenderTargets(1, &target, nullptr);
        const float transparent[4] = {};
        context->ClearRenderTargetView(target, transparent);
        active = true;
        return true;
    }

    // 恢复原画布并整体混合这一行；调用方随后恢复 ImGui 的渲染状态。
    void End(ID3D11DeviceContext* context, float opacity) {
        if (!active) return;
        context->OMSetRenderTargets(D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT, savedTargets, savedDepth);
        for (auto& saved : savedTargets) Release(saved);
        Release(savedDepth);
        active = false;
        D3D11_MAPPED_SUBRESOURCE mapped = {};
        if (FAILED(context->Map(opacityBuffer, 0, D3D11_MAP_WRITE_DISCARD, 0, &mapped))) return;
        const float values[4] = { opacity, 0, 0, 0 };
        memcpy(mapped.pData, values, sizeof(values));
        context->Unmap(opacityBuffer, 0);
        ID3D11Buffer* savedBuffer = nullptr;
        ID3D11ShaderResourceView* savedView = nullptr;
        context->PSGetConstantBuffers(0, 1, &savedBuffer);
        context->PSGetShaderResources(0, 1, &savedView);
        context->IASetInputLayout(nullptr);
        context->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
        context->VSSetShader(vertexShader, nullptr, 0);
        context->PSSetShader(pixelShader, nullptr, 0);
        context->PSSetConstantBuffers(0, 1, &opacityBuffer);
        context->PSSetShaderResources(0, 1, &view);
        const float factors[4] = {};
        context->OMSetBlendState(blend, factors, 0xffffffff);
        const D3D11_RECT fullRect = { 0, 0, (LONG)width, (LONG)height };
        context->RSSetScissorRects(1, &fullRect);
        context->Draw(3, 0);
        context->PSSetConstantBuffers(0, 1, &savedBuffer);
        context->PSSetShaderResources(0, 1, &savedView);
        Release(savedBuffer);
        Release(savedView);
    }
};
