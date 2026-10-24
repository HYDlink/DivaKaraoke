#include <cstdio>
#include <cstdlib>
#include <vector>
#include <cmath>
#include <fstream>
#include <string>
#include <Windows.h>
#include <imgui.h>
#include <imgui_impl_dx11.h>
#include "../Source/managers/ktv_composite.h"
#include "../Source/managers/ktv_timing.h"
#include "../Source/managers/ktv_geometry.h"
#include "../Source/managers/singer_style.h"
#include "../Source/managers/singer_render.h"

static ID3D11Device* device = nullptr;
static ID3D11DeviceContext* context = nullptr;
static KtvCompositeLayer layer;
static bool began = false;
static constexpr UINT width = 256, height = 128;

// 布局检查只需要行级时间，不依赖字幕文本或字级同步数据。
struct TimingLine {
    // 句子开始时间，单位毫秒。
    long startMs;
    // 句子结束时间，单位毫秒。
    long endMs;
};

// 字号检查使用与游戏旁路文件一致的 Ruby 数据结构。
struct GeometryRubySpan {
    // UTF-16 字符起点。
    size_t start;
    // 所属汉字组长度。
    size_t length;
    // 振假名文本。
    std::string ruby;
};

// 保留整句时间，只临时调整绘制尺寸的检查样本。
struct GeometryLine {
    // 正文文本。
    std::string text;
    // 振假名词组。
    std::vector<GeometryRubySpan> rubySpans;
};

static const GeometryLine longLine = { u8"「おはよう」挨拶交わす君の頭上にねこみみ",
    { {6, 2, u8"あいさつ"}, {8, 1, u8"か"}, {11, 1, u8"きみ"}, {13, 2, u8"ずじょう"} } };

// 检查断言并用中文报告失败原因。
void Require(bool condition, const char* description) {
    if (!condition) { printf("检查失败：%s\n", description); exit(1); }
}

// 读取既有 PV824 SRT 的行时间，复现用户反馈的 1:58 间奏结束场景。
std::vector<TimingLine> ReadLayoutFixture() {
    std::ifstream input("testdata/PV824.ktv-layout.srt");
    Require(input.is_open(), "PV824 布局样本读取");
    std::vector<TimingLine> result;
    std::string line;
    while (std::getline(input, line)) {
        long sh, sm, ss, sms, eh, em, es, ems;
        if (std::sscanf(line.c_str(), "%ld:%ld:%ld,%ld --> %ld:%ld:%ld,%ld",
            &sh, &sm, &ss, &sms, &eh, &em, &es, &ems) == 8)
            result.push_back({ ((sh * 60 + sm) * 60 + ss) * 1000 + sms,
                ((eh * 60 + em) * 60 + es) * 1000 + ems });
    }
    return result;
}

// 验证长间奏分段、短停顿交替、真实同轨衔接和待唱行的提示点位置。
void VerifyKtvLayout() {
    Require(!IsKtvParagraphBreak(17999, 10000) && IsKtvParagraphBreak(18000, 10000), "八秒分段边界");
    const auto fixture = ReadLayoutFixture();
    const auto actual = BuildKtvLineLayouts(fixture, 3000);
    Require(actual.size() == 34 && fixture[19].startMs == 118538, "PV824 第 20 句起唱时间");
    Require(actual[19].lane == 0 && actual[20].lane == 1, "PV824 长间奏后第一句上轨、第二句下轨");
    Require(actual[19].fadeInStartMs == 112538 && actual[20].fadeInStartMs == 112538, "新段落两句在开唱前六秒同步淡入");
    Require(actual[18].nextSameLaneStartMs == 118538, "重置后连续上轨通过实际轨道关联旧句");
    Require(actual[0].lane == 0 && actual[1].lane == 1 && actual[2].lane == 0, "段落内部保持交替");
    const auto shortGap = BuildKtvLineLayouts(std::vector<TimingLine>{ {1000, 3000}, {4500, 7000}, {9000, 12000} }, 3000);
    Require(shortGap[1].lane == 1 && shortGap[2].lane == 0, "短停顿不重置段落");
    Require(std::fabs(GetKtvCountdownRowY(shortGap[1].lane, 0.66f, 0.83f) - 0.765f) < 0.001f, "下轨待唱句的提示点在下轨上方");
    Require(std::fabs(GetKtvCountdownRowY(actual[19].lane, 0.66f, 0.83f) - 0.595f) < 0.001f, "新段落提示点跟随上轨首句");
    const float dotsX = GetKtvCountdownFirstX(1700, 154, 1766, 1);
    Require(dotsX >= 168 && dotsX + 210 + 14 <= 1766, "短歌词提示点仍处于左右安全边距内");
    const auto evenParagraph = BuildKtvLineLayouts(std::vector<TimingLine>{ {1000, 3000}, {3000, 5000}, {15000, 17000}, {17000, 19000} }, 3000);
    Require(evenParagraph[2].lane == 0 && evenParagraph[3].lane == 1, "偶数句段落结束后也从上轨开始");
    const auto wideNearbyWindow = BuildKtvLineLayouts(std::vector<TimingLine>{ {1000, 3000}, {13000, 17000} }, 12000);
    Require(wideNearbyWindow[1].fadeInStartMs == 7000, "相邻阈值加大仍不能把新段歌词提前到六秒窗口之外");
    printf("段落布局检查通过：PV824 第 20 句上轨，第 21 句下轨；短停顿提示点跟随待唱句。\n");
}

// 检查真实字形的绘制顶点，确保正文和描边没有突破安全边距。
void VerifyGeometryVertices(ImFont* font, const GeometryLine& line, const KtvGeometryStyle& style,
    const KtvLineGeometry& geometry, float left, float right) {
    ImDrawList drawing(ImGui::GetDrawListSharedData());
    drawing._ResetForNewFrame();
    drawing.PushTextureID(font->ContainerAtlas->TexID);
    drawing.PushClipRect(ImVec2(-10000, -10000), ImVec2(10000, 10000));
    const float scale = geometry.fontSize / style.referenceFontSize;
    const int outline = (std::max)(1, (int)roundf(style.strokeSize * scale));
    drawing.AddText(font, geometry.fontSize,
        ImVec2(geometry.position.x + style.shadowOffset.x * scale, geometry.position.y + style.shadowOffset.y * scale),
        IM_COL32_WHITE, line.text.c_str());
    for (int y = -outline; y <= outline; y++) for (int x = -outline; x <= outline; x++)
        drawing.AddText(font, geometry.fontSize, ImVec2(geometry.position.x + x, geometry.position.y + y), IM_COL32_WHITE, line.text.c_str());
    Require(drawing.VtxBuffer.Size > 0, "实际字形绘制顶点生成");
    for (const ImDrawVert& vertex : drawing.VtxBuffer)
        Require(vertex.pos.x >= left && vertex.pos.x <= right, "正文描边与阴影绘制顶点位于安全区");
}

// 在真实日文字体的 94 号字下检查长句适配、普通句恢复、Ruby 和 4K 缩放。
void VerifyKtvGeometry(ImFont* epson, ImFont* dfp, ImFont* epson4k) {
    const GeometryLine shortLine = { u8"寝ぼけてるのさ", {{0, 1, u8"ね"}} };
    for (ImFont* font : { epson, dfp }) {
        for (bool background : { false, true }) {
            for (ImVec2 shadow : { ImVec2(3, 3), ImVec2(-12, -3) }) {
                const KtvGeometryStyle style = {94, 4, shadow, background ? 18.0f : 0.0f, 1};
                const float left = 1920 * 0.08f, right = 1920 * 0.92f;
                const float originalWidth = MeasureKtvLineBounds(font, 94, longLine, style).z
                    - MeasureKtvLineBounds(font, 94, longLine, style).x;
                for (int lane : {0, 1}) {
                    const auto fitted = GetKtvLineGeometry(font, 94, longLine, style, lane, left, right, lane == 0 ? 713 : 896);
                    Require(fitted.fontSize > 0 && fitted.fontSize <= 94, "长句只缩小临时字号");
                    if (originalWidth > right - left) Require(fitted.fontSize < 94, "超宽句确实缩小");
                    Require(fitted.position.x + fitted.bounds.x >= left && fitted.position.x + fitted.bounds.z <= right, "正文 Ruby 背景包围盒位于安全区");
                    VerifyGeometryVertices(font, longLine, style, fitted, left, right);
                    const auto normal = GetKtvLineGeometry(font, 94, shortLine, style, lane, left, right, 713);
                    Require(normal.fontSize == 94, "后面的短句自动恢复 94 号字");
                    ImVec2 rubyPosition;
                    float rubySize, groupWidth;
                    Require(GetKtvRubyGeometry(font, fitted.fontSize, longLine.text.c_str(), longLine.rubySpans[0], style,
                        rubyPosition, rubySize, groupWidth), "振假名使用适配后的正文尺寸");
                    Require(rubySize <= fitted.fontSize * 0.42f + 0.001f, "振假名同比缩放并保持词组范围");
                }
            }
        }
        const KtvGeometryStyle style = {94, 4, ImVec2(3, 3), 0, 1};
        const auto fitted = GetKtvLineGeometry(font, 94, longLine, style, 0, 153.6f, 1766.4f, 713);
        printf("94 号字长句适配检查通过，临时字号 %.2f。\n", fitted.fontSize);
    }
    const KtvGeometryStyle fourKStyle = {94, 4, ImVec2(3, 3), 0, 2};
    const auto fourK = GetKtvLineGeometry(epson4k, 188, longLine, fourKStyle, 1, 3840 * 0.08f, 3840 * 0.92f, 1793);
    Require(fourK.position.x + fourK.bounds.x >= 3840 * 0.08f && fourK.position.x + fourK.bounds.z <= 3840 * 0.92f,
        "4K 高分辨率字体图集的长句完整位于安全区");
    VerifyGeometryVertices(epson4k, longLine, fourKStyle, fourK, 3840 * 0.08f, 3840 * 0.92f);
    const KtvGeometryStyle style = {94, 4, ImVec2(3, 3), 0, 1};
    const auto invalid = GetKtvLineGeometry(epson, 94, longLine, style, 0, 100, 100, 0);
    Require(invalid.fontSize == 0, "无有效宽度时安全跳过绘制");
    printf("长句宽度检查通过：两种日文字体、上下轨、Ruby、描边、背景、负向阴影及 4K。\n");
}

// 在真实 DX11 命令执行时开始透明合成。
void BeginLayer(const ImDrawList*, const ImDrawCmd*) {
    began = layer.Begin(device, context);
    Require(began, "透明合成纹理和着色器创建");
}

// 完成整体透明合成。
void EndLayer(const ImDrawList*, const ImDrawCmd* command) {
    layer.End(context, (float)(uintptr_t)command->UserCallbackData / 65535.0f);
}

// 读回实际 GPU 输出，支持非连续的显存行跨度。
std::vector<unsigned char> ReadPixels(ID3D11Texture2D* texture) {
    D3D11_TEXTURE2D_DESC description;
    texture->GetDesc(&description);
    description.BindFlags = 0;
    description.Usage = D3D11_USAGE_STAGING;
    description.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    ID3D11Texture2D* staging = nullptr;
    Require(SUCCEEDED(device->CreateTexture2D(&description, nullptr, &staging)), "读回纹理创建");
    context->CopyResource(staging, texture);
    D3D11_MAPPED_SUBRESOURCE mapped;
    Require(SUCCEEDED(context->Map(staging, 0, D3D11_MAP_READ, 0, &mapped)), "读回纹理映射");
    std::vector<unsigned char> result(width * height * 4);
    for (UINT y = 0; y < height; y++)
        memcpy(result.data() + y * width * 4, (unsigned char*)mapped.pData + y * mapped.RowPitch, width * 4);
    context->Unmap(staging, 0);
    staging->Release();
    return result;
}


// 验证分带裁剪没有缺口、重叠或纹理错位，注音单独使用自身真实字形边界。
void VerifyVerticalSingerGlyphs(ImFont* font) {
    std::map<std::string, SingerPalette> palettes = { {"MIK",DefaultSingerPalette("MIK")}, {"RIN",DefaultSingerPalette("RIN")}, {"LUK",DefaultSingerPalette("LUK")} };
    palettes["MIK"].afterStroke = ImVec4(0.4f,0.1f,0.2f,0.4f);
    palettes["RIN"].afterStroke = ImVec4(0.1f,0.2f,0.6f,0.9f);
    const KtvTextStyle fallback = { ImVec4(1,1,1,1),ImVec4(0,0,0,1),ImVec4(0,0,0,0.5f) };
    for (float size : {18.0f,94.0f,188.0f}) for (bool after : {false,true}) for (int people : {2,3}) for (int layerIndex=0;layerIndex<3;++layerIndex) {
        const std::vector<std::string> ids = people==2 ? std::vector<std::string>{"MIK","RIN"} : std::vector<std::string>{"MIK","RIN","LUK"};
        const auto style = ResolveSingerStyle(ids,palettes,after,true,fallback,10,500,true);
        const auto& stops = layerIndex==0 ? style.fillStops : layerIndex==1 ? style.strokeStops : style.shadowStops;
        const ImVec2 position(10.7f,21.8f);
        const char* text = size==18 ? u8"ねぼ" : u8"寝ぼけ";
        const float clipX = 10 + font->CalcTextSizeA(size,FLT_MAX,0,text).x*0.67f;
        ImDrawList reference(ImGui::GetDrawListSharedData()), actual(ImGui::GetDrawListSharedData());
        for (auto* draw : {&reference,&actual}) {
            draw->_ResetForNewFrame(); draw->PushTextureID(font->ContainerAtlas->TexID);
            draw->PushClipRect(ImVec2(0,0),ImVec2(clipX,1000));
        }
        const ImVec4 clip(0,0,clipX,1000);
        bool distinct=false;
        for(const auto& stop:stops) distinct=distinct || stop.x!=stops.front().x || stop.y!=stops.front().y || stop.z!=stops.front().z || stop.w!=stops.front().w;
        reference.AddText(font,size,position,IM_COL32_WHITE,text,nullptr,0,distinct?&clip:nullptr);
        AddSingerStyledText(&actual,font,size,position,text,style,layerIndex,0.5f);
        Require(actual.VtxBuffer.Size>0 && actual.VtxBuffer.Size%4==0,"上下渐变没有有效字形四边形");
        double sourceArea=0,actualArea=0;
        for (int k=0;k<reference.VtxBuffer.Size;k+=4) sourceArea+=(reference.VtxBuffer[k+2].pos.x-reference.VtxBuffer[k].pos.x)*(reference.VtxBuffer[k+2].pos.y-reference.VtxBuffer[k].pos.y);
        const ImVec2 ink=GetSingerInkY(font,size,text,position.y);
        for(int k=0;k<actual.VtxBuffer.Size;k+=4){
            const auto& begin=actual.VtxBuffer[k];const auto& end=actual.VtxBuffer[k+2];
            actualArea+=(end.pos.x-begin.pos.x)*(end.pos.y-begin.pos.y);
            int source=-1;
            for(int j=0;j<reference.VtxBuffer.Size;j+=4){const auto& a=reference.VtxBuffer[j];const auto& b=reference.VtxBuffer[j+2];
                if(std::fabs(a.pos.x-begin.pos.x)<0.001f && std::fabs(b.pos.x-end.pos.x)<0.001f && begin.pos.y>=a.pos.y-0.001f && end.pos.y<=b.pos.y+0.001f){source=j;break;}}
            Require(source>=0,"上下色带越出原始字形范围");
            const auto& a=reference.VtxBuffer[source];const auto& b=reference.VtxBuffer[source+2];
            for(int corner=0;corner<4;++corner){const auto& v=actual.VtxBuffer[k+corner];
                const float u=a.uv.x+(b.uv.x-a.uv.x)*(v.pos.x-a.pos.x)/(b.pos.x-a.pos.x);
                const float uvY=a.uv.y+(b.uv.y-a.uv.y)*(v.pos.y-a.pos.y)/(b.pos.y-a.pos.y);
                Require(std::fabs(v.uv.x-u)<0.00001f && std::fabs(v.uv.y-uvY)<0.00001f,"上下裁剪没有正确插值字体UV");
                ImVec4 expected=SampleSingerGradient(stops,(v.pos.y-ink.x)/(ink.y-ink.x),0.20f); expected.w*=0.5f;
                Require(v.col==ImGui::ColorConvertFloat4ToU32(expected),"上下渐变层颜色或透明度不匹配");
            }
        }
        Require(std::fabs(sourceArea-actualArea)<(std::max)(0.02,sourceArea*0.00001),"上下色带存在面积缺口或重叠");
    }
    printf("上下双色检查通过：两人/三人、完整四色与阴影、正文/注音、18/94/188字号、UV与色带覆盖。\n");
}


// 密集描边可能超过16位顶点索引容量，验证现有DX11顶点偏移路径仍正确。
void VerifyVerticalIndexOffsets(ImFont* font) {
    ImDrawList list(ImGui::GetDrawListSharedData());
    list._ResetForNewFrame(); list.PushTextureID(font->ContainerAtlas->TexID);
    list.PushClipRect(ImVec2(0,0),ImVec2(10000,1000));
    Require((list.Flags & ImDrawListFlags_AllowVtxOffset)!=0,"现有后端缺少大字形顶点偏移支持");
    const std::map<std::string,SingerPalette> palettes={{"MIK",DefaultSingerPalette("MIK")},{"RIN",DefaultSingerPalette("RIN")}};
    const KtvTextStyle fallback={ImVec4(1,1,1,1),ImVec4(0,0,0,1),ImVec4(0,0,0,0.5f)};
    const auto style=ResolveSingerStyle({"MIK","RIN"},palettes,false,true,fallback,10,10000,true);
    std::string text;
    for(int index=0;index<30;++index)text+=u8"寝";
    for(int run=0;run<120;++run)AddSingerStyledText(&list,font,188,ImVec2(10,20),text.c_str(),style,1,1);
    Require(list.VtxBuffer.Size>65535,"大字号验证未跨过索引边界");
    bool offsetUsed=false;
    for(const auto& command:list.CmdBuffer){
        offsetUsed=offsetUsed || command.VtxOffset>0;
        for(unsigned int index=0;index<command.ElemCount;++index)
            Require(command.VtxOffset+list.IdxBuffer[command.IdxOffset+index]<(unsigned int)list.VtxBuffer.Size,"上下渐变存在越界顶点索引");
    }
    Require(offsetUsed,"超过16位容量后没有切换顶点偏移");
    printf("大字号索引检查通过：%d个顶点，密集描边超过16位容量仍正确。\n",list.VtxBuffer.Size);
}

// 使用共享生产入口复现合唱描边、阴影与填充，并保持原有横向裁剪。
void DrawRegressionSingerText(ImDrawList* list,ImFont* font,const KtvTextStyle& style){
    AddSingerStyledText(list,font,64,ImVec2(34,27),u8"合唱",style,2,1);
    for(int y=-3;y<=3;++y)for(int x=-3;x<=3;++x)if(x||y)
        AddSingerStyledText(list,font,64,ImVec2(32.0f+x,24.0f+y),u8"合唱",style,1,1);
    AddSingerStyledText(list,font,64,ImVec2(32,24),u8"合唱",style,0,1);
}

// 在软件 DX11 设备中复现密集描边，然后对整个结果应用透明度。
std::vector<unsigned char> Render(ID3D11Texture2D* texture, ID3D11RenderTargetView* target, float opacity, bool composite, bool singerGradient = false, bool vertical = false, float progress = 1.0f) {
    const float background[4] = { 0.2f, 0.4f, 0.6f, 1.0f };
    context->OMSetRenderTargets(1, &target, nullptr);
    context->ClearRenderTargetView(target, background);
    ImGui_ImplDX11_NewFrame();
    ImGui::NewFrame();
    ImDrawList* list = ImGui::GetForegroundDrawList();
    if (composite) list->AddCallback(BeginLayer, nullptr);
    const int alpha = composite ? 255 : (int)(opacity * 255);
    ImFont* font = ImGui::GetIO().Fonts->Fonts[0];
    if (vertical) {
        font = ImGui::GetIO().Fonts->Fonts[1];
        const std::map<std::string,SingerPalette> palettes = {{"MIK",DefaultSingerPalette("MIK")},{"RIN",DefaultSingerPalette("RIN")}};
        const KtvTextStyle fallback = {ImVec4(1,1,1,1),ImVec4(0,0,0,1),ImVec4(0,0,0,0.5f)};
        const float textWidth=font->CalcTextSizeA(64,FLT_MAX,0,u8"合唱").x;
        for(bool after : {true,false}) {
            if ((after && progress<=0) || (!after && progress>=1)) continue;
            const auto style=ResolveSingerStyle({"MIK","RIN"},palettes,after,true,fallback,32,textWidth,true);
            const ImVec2 clipMin=list->GetClipRectMin(),clipMax=list->GetClipRectMax();
            list->PushClipRect(ImVec2(after?clipMin.x:32+textWidth*progress,clipMin.y),ImVec2(after?32+textWidth*progress:clipMax.x,clipMax.y),true);
            DrawRegressionSingerText(list,font,style);
            list->PopClipRect();
        }
    } else {
    for (int y = -5; y <= 5; y++)
        for (int x = -5; x <= 5; x++)
            if (x || y) list->AddText(font, 64, ImVec2(32.0f + x, 24.0f + y), IM_COL32(0, 0, 0, alpha), "KTV");
    const int fillFirst = list->VtxBuffer.Size;
    list->AddText(font, 64, ImVec2(32, 24), IM_COL32(255, 240, 80, alpha), "KTV");
    if (singerGradient) ApplySingerVertexGradient(list, fillFirst,
        { DefaultSingerPalette("MIK").afterFill, DefaultSingerPalette("RIN").afterFill },
        32, font->CalcTextSizeA(64, FLT_MAX, 0, "KTV").x, composite ? 1.0f : opacity);
    }
    if (composite) {
        list->AddCallback(EndLayer, (void*)(uintptr_t)(opacity * 65535));
        list->AddCallback(ImDrawCallback_ResetRenderState, nullptr);
    }
    // 在合成层之后绘制另一块不透明标记，检查 ImGui 状态恢复。
    list->AddRectFilled(ImVec2(230, 100), ImVec2(250, 120), IM_COL32(255, 0, 0, 255));
    ImGui::Render();
    ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());
    return ReadPixels(texture);
}

// 将多个透明度阶段写为便于查看的 BMP；上排为整体合成，下排为旧式逐层透明。
void SaveComparison(const std::vector<std::vector<unsigned char>>& frames) {
    BITMAPFILEHEADER file = {};
    BITMAPINFOHEADER information = {};
    information.biSize = sizeof(information);
    information.biWidth = width * 4;
    information.biHeight = -(LONG)(height * 2);
    information.biPlanes = 1;
    information.biBitCount = 32;
    file.bfType = 0x4d42;
    file.bfOffBits = sizeof(file) + sizeof(information);
    file.bfSize = file.bfOffBits + width * height * 4 * 8;
    std::ofstream output("artifacts/lyric-composite-fix-build/ktv-composite-comparison.bmp", std::ios::binary);
    Require(output.is_open(), "透明合成对照图创建");
    output.write((char*)&file, sizeof(file));
    output.write((char*)&information, sizeof(information));
    for (UINT row = 0; row < height * 2; row++) {
        for (UINT column = 0; column < 4; column++) {
            const auto& frame = frames[(row / height) * 4 + column];
            for (UINT x = 0; x < width; x++) {
                const unsigned char* pixel = frame.data() + ((row % height) * width + x) * 4;
                const unsigned char bgra[4] = { pixel[2], pixel[1], pixel[0], pixel[3] };
                output.write((const char*)bgra, 4);
            }
        }
    }
}

// 保存实际DX11字形渐变预览，供肉眼检查融合颜色及字体边缘。
void SaveSingerGradientFrame(const std::vector<unsigned char>& pixels, const char* filename = "artifacts/singer-mvp/gradient-preview.bmp") {
    BITMAPFILEHEADER file{}; BITMAPINFOHEADER info{};
    info.biSize = sizeof(info); info.biWidth = width; info.biHeight = -(LONG)height;
    info.biPlanes = 1; info.biBitCount = 32;
    file.bfType = 0x4d42; file.bfOffBits = sizeof(file) + sizeof(info); file.bfSize = file.bfOffBits + width * height * 4;
    std::ofstream output(filename, std::ios::binary);
    Require(output.is_open(), "歌手渐变预览文件创建");
    output.write((char*)&file, sizeof(file)); output.write((char*)&info, sizeof(info));
    for (size_t index = 0; index < pixels.size(); index += 4) {
        const unsigned char bgra[] = { pixels[index + 2], pixels[index + 1], pixels[index], pixels[index + 3] };
        output.write((const char*)bgra, 4);
    }
}

// 验证时间门限和真实透明合成，不启动游戏或改变游戏配置。
int main() {
    SetConsoleOutputCP(CP_UTF8);
    VerifyKtvLayout();
    Require(GetLyricFadeOpacity(13750, 4000, 12000) == 0.5f, "结束后保留 1.5 秒再半秒淡出");
    Require(GetLyricFadeOpacity(13499, 4000, 12000) == 1.0f, "保留期间透明度稳定");
    Require(GetLyricFadeOpacity(14000, 4000, 12000) == 0.0f, "淡出终点");
    Require(GetLyricFadeOpacity(4250, 4000, 12000) == 0.5f, "半秒淡入");
    Require(GetKtvWipeProgress(13750, 10000, 12000) == 1.0f, "淡出时保留已唱颜色");
    const long firstStart = GetKtvFadeInStart(10000, false, 0, false, 0);
    Require(firstStart == 4000, "首句前六秒显影");
    Require(GetKtvFadeInStart(1333, false, 0, false, 0) == 0, "开场立即开唱的歌曲仍从播放起点淡入");
    Require(GetKtvFadeInStart(12500, true, firstStart, false, 0) == firstStart, "短间隔首两句同时淡入");
    Require(GetKtvFadeInStart(18000, true, firstStart, true, 12000) == 14000, "同轨旧句淡完再显示新句");
    Require(GetKtvFadeInStart(13500, true, firstStart, true, 12000) == 13000, "密集短句仍能在开唱前完成淡入");
    Require(GetLyricFadeOpacity(12750, 4000, 12000, 13500) == 0.5f, "密集短句旧句也经过半秒淡出");
    Require(!ShouldDrawKtvCountdown(false, 6001) && ShouldDrawKtvCountdown(false, 6000), "长空档六秒提示门限");
    Require(!ShouldDrawKtvCountdown(true, 1500) && ShouldDrawKtvCountdown(false, 1500), "短空档提示保留");
    D3D_FEATURE_LEVEL level;
    Require(SUCCEEDED(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0, nullptr, 0,
        D3D11_SDK_VERSION, &device, &level, &context)), "软件 DX11 设备创建");
    D3D11_TEXTURE2D_DESC description = {};
    description.Width = width;
    description.Height = height;
    description.MipLevels = description.ArraySize = description.SampleDesc.Count = 1;
    description.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    description.BindFlags = D3D11_BIND_RENDER_TARGET;
    ID3D11Texture2D* texture = nullptr;
    ID3D11RenderTargetView* target = nullptr;
    Require(SUCCEEDED(device->CreateTexture2D(&description, nullptr, &texture)), "测试画布创建");
    Require(SUCCEEDED(device->CreateRenderTargetView(texture, nullptr, &target)), "测试视图创建");
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.DisplaySize = ImVec2((float)width, (float)height);
    io.DeltaTime = 1.0f / 60;
    io.IniFilename = nullptr;
    io.Fonts->AddFontDefault();
    ImFontGlyphRangesBuilder builder;
    builder.AddText(longLine.text.c_str());
    builder.AddText(u8"合唱ねぼ");
    builder.AddText(u8"寝ぼけてるのさあいさつかきみずじょう");
    ImVector<ImWchar> japaneseRanges;
    builder.BuildRanges(&japaneseRanges);
    ImFont* epson = io.Fonts->AddFontFromFileTTF("E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/fonts/03-epson-marugothic-bold.ttf", 94, nullptr, japaneseRanges.Data);
    ImFontConfig dfpConfiguration;
    dfpConfiguration.FontNo = 2;
    ImFont* dfp = io.Fonts->AddFontFromFileTTF("E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/fonts/02-dfp-maru-gothic-sb.ttc", 94, &dfpConfiguration, japaneseRanges.Data);
    ImFont* epson4k = io.Fonts->AddFontFromFileTTF("E:/SteamLibrary/steamapps/common/Hatsune Miku Project DIVA Mega Mix Plus/mods/MMFreeLyrics/fonts/03-epson-marugothic-bold.ttf", 188, nullptr, japaneseRanges.Data);
    Require(epson && dfp && epson4k && io.Fonts->Build(), "日文字体真实字形图集构建");
    ImGui_ImplDX11_Init(device, context);
    ImGui_ImplDX11_NewFrame();
    ImGui::NewFrame();
    // 使用真实字形验证顶点渐变可作用于正文与小字号，且不会重建或破坏UV。
    std::map<std::string, SingerPalette> palettes = { { "MIK", DefaultSingerPalette("MIK") }, { "RIN", DefaultSingerPalette("RIN") }, { "LUK", DefaultSingerPalette("LUK") } };
    const KtvTextStyle fallback = { ImVec4(1,1,1,1), ImVec4(0,0,0,1), ImVec4(0,0,0,0.5f) };
    const auto duet = ResolveSingerStyle({ "MIK", "RIN", "MIK" }, palettes, true, true, fallback, 10, 150);
    Require(duet.fillStops.size() == 2 && duet.strokeStops.size() == 2, "同身份去重并保留填充及描边双端点");
    Require(ResolveSingerStyle({ "MIK", "RIN", "LUK" }, palettes, false, true, fallback, 10, 150).fillStops.size() == 3, "三人组合渐变未支持");
    Require(ResolveSingerStyle({}, palettes, true, true, fallback, 10, 150).fillStops.empty(), "未标记歌词没有回退默认样式");
    Require(ResolveSingerStyle({"MIK","RIN"}, palettes, true, false, fallback, 10, 150).fillStops.empty(), "关闭渐变未使用融合纯色");
    for (float textSize : { 18.0f, 94.0f, 188.0f }) {
        ImDrawList glyphList(ImGui::GetDrawListSharedData());
        glyphList._ResetForNewFrame(); glyphList.PushTextureID(io.Fonts->TexID); glyphList.PushClipRectFullScreen();
        glyphList.AddText(epson, textSize, ImVec2(10, 10), IM_COL32_WHITE, u8"寝ぼけてるのさ");
        Require(glyphList.VtxBuffer.Size > 0, "实际字形没有产生顶点");
        const ImVec2 uv = glyphList.VtxBuffer[0].uv;
        ApplySingerVertexGradient(&glyphList, 0, duet.fillStops, 10, 150, 0.5f);
        Require(glyphList.VtxBuffer[0].uv.x == uv.x && glyphList.VtxBuffer[0].uv.y == uv.y, "渐变破坏字体纹理覆盖率");
        Require(((glyphList.VtxBuffer[0].col >> IM_COL32_A_SHIFT) & 255) >= 127 && ((glyphList.VtxBuffer[0].col >> IM_COL32_A_SHIFT) & 255) <= 128, "渐变透明度没有同步应用");
    }
    printf("歌手渐变检查通过：单人回退、双人去重、三人组合、描边与18/94/188字号字形。\n");
    VerifyVerticalSingerGlyphs(epson);
    VerifyVerticalIndexOffsets(epson4k);
    VerifyKtvGeometry(epson, dfp, epson4k);
    ImGui::EndFrame();
    auto reference = Render(texture, target, 1.0f, true);
    auto direct = Render(texture, target, 1.0f, false);
    int opaqueError = 0;
    for (UINT y = 0; y < 90; y++) for (UINT x = 0; x < width; x++) for (int channel = 0; channel < 3; channel++) {
        const size_t offset = (y * width + x) * 4 + channel;
        opaqueError = (std::max)(opaqueError, std::abs((int)reference[offset] - (int)direct[offset]));
    }
    Require(opaqueError <= 3, "不透明阶段与原有字色一致，允许纹理量化误差");
    const int background[3] = { 51, 102, 153 };
    std::vector<std::vector<unsigned char>> frames;
    int maximumError = 0;
    for (float opacity : { 0.25f, 0.5f, 0.75f, 1.0f }) {
        auto pixels = Render(texture, target, opacity, true);
        for (UINT y = 0; y < 90; y++) for (UINT x = 0; x < width; x++) for (int channel = 0; channel < 3; channel++) {
            const size_t offset = (y * width + x) * 4 + channel;
            const float expected = background[channel] + opacity * (reference[offset] - background[channel]);
            const int error = (int)std::ceil(std::fabs(pixels[offset] - expected));
            maximumError = (std::max)(maximumError, error);
            Require(error <= 2, "颜色必须按整层透明度线性混合，而非黑色变亮");
        }
        const size_t marker = (110 * width + 240) * 4;
        Require(pixels[marker] == 255 && pixels[marker + 1] == 0 && pixels[marker + 2] == 0, "合成后 ImGui 渲染状态恢复");
        frames.push_back(std::move(pixels));
    }
    for (float opacity : { 0.25f, 0.5f, 0.75f, 1.0f }) frames.push_back(Render(texture, target, opacity, false));
    SaveComparison(frames);
    SaveSingerGradientFrame(Render(texture, target, 1.0f, true, true));
    const auto verticalReference=Render(texture,target,1.0f,true,false,true);
    const auto verticalHalf=Render(texture,target,0.5f,true,false,true);
    int verticalError=0;
    for(UINT y=0;y<90;++y)for(UINT x=0;x<width;++x)for(int channel=0;channel<3;++channel){
        const size_t index=(y*width+x)*4+channel;
        const int error=(int)std::ceil(std::fabs(verticalHalf[index]-(background[channel]+0.5f*(verticalReference[index]-background[channel]))));
        verticalError=(std::max)(verticalError,error);
    }
    Require(verticalError<=2,"上下渐变破坏整层透明合成");
    SaveSingerGradientFrame(verticalReference,"artifacts/singer-mvp/vertical-gradient-preview.bmp");
    SaveSingerGradientFrame(Render(texture,target,1.0f,true,false,true,0.18f),"artifacts/singer-mvp/vertical-start-preview.bmp");
    printf("上下双色真实DX11渲染通过：最大透明合成误差%d/255。\n",verticalError);
    ImGui_ImplDX11_Shutdown();
    ImGui::DestroyContext();
    target->Release(); texture->Release(); context->Release(); device->Release();
    printf("时间逻辑检查通过；DX11 整层透明合成检查通过，最大通道误差 %d/255。\n", maximumError);
    return 0;
}
