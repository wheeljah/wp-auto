"""wp-auto/image — 상업용 무료 이미지 자동 fetch/embed pipeline.

Phase 1-5 통합:
- source_resolver: Pexels + Wikimedia + NASA (상업용 무료)
- generator: PIL 자체 infographic (키워드/제목 기반)
- embedder: HTML 초안 <figure> 자동 삽입 + WebP 변환
- pipeline: orchestrator (search → download → embed)

사용법:
    from wp_auto.image.pipeline import ImagePipeline
    pipe = ImagePipeline(
        assets_dir=Path("assets/images"),
        pexels_api_key=os.environ["PEXELS_API_KEY"],
    )
    result = pipe.run(draft_html, keyword="GPT-6", max_images=2)
    final_html = result["html"]
"""
