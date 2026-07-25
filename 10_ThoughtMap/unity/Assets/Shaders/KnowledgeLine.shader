Shader "ThoughtMap/KnowledgeLine"
{
    Properties
    {
        _BaseColor ("Data Color", Color) = (0.1,0.6,1,1)
        _Glow ("Soft Glow", Range(0,8)) = 2
        _FlowSpeed ("UV Flow", Range(-8,8)) = 2
        _FlowScale ("Flow Scale", Range(1,32)) = 12
        _Softness ("Edge Softness", Range(0.05,1)) = 0.45
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent+20" "RenderPipeline"="UniversalPipeline" }
        Blend SrcAlpha One
        ZWrite Off
        Cull Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            struct Attributes { float4 positionOS:POSITION; float2 uv:TEXCOORD0; float3 normalOS:NORMAL; };
            struct Varyings { float4 positionHCS:SV_POSITION; float2 uv:TEXCOORD0; float fresnel:TEXCOORD1; };
            CBUFFER_START(UnityPerMaterial)
            float4 _BaseColor; float _Glow; float _FlowSpeed; float _FlowScale; float _Softness;
            CBUFFER_END
            Varyings vert(Attributes i)
            {
                Varyings o; o.positionHCS=TransformObjectToHClip(i.positionOS.xyz); o.uv=i.uv;
                float3 n=TransformObjectToWorldNormal(i.normalOS); float3 v=GetWorldSpaceNormalizeViewDir(TransformObjectToWorld(i.positionOS.xyz));
                o.fresnel=pow(1-saturate(dot(n,v)),2); return o;
            }
            half4 frag(Varyings i):SV_Target
            {
                float edge=saturate(1-abs(i.uv.y*2-1)); edge=smoothstep(0, max(.05,_Softness), edge);
                float flow=.55+.45*sin((i.uv.x*_FlowScale-_Time.y*_FlowSpeed)*6.28318);
                float intensity=(edge*(.6+flow*.4)+i.fresnel*.25)*_Glow;
                return half4(_BaseColor.rgb*intensity, saturate(edge*_BaseColor.a));
            }
            ENDHLSL
        }
    }
    Fallback "Sprites/Default"
}
