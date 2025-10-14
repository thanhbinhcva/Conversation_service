from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

def generate_logo_with_ai(brand_profile, google_api_key, output_path="generated_image.png"):
    """
    Gọi Gemini API để tạo logo cách điệu từ thông tin thương hiệu.
    
    Args:
        brand_profile (dict): Hồ sơ thương hiệu (chứa brand_name_full, logo_style, main_color)
        google_api_key (str): API key của Google AI Studio
        output_path (str): Đường dẫn lưu ảnh kết quả
        
    Returns:
        str: Đường dẫn file ảnh đã lưu hoặc None nếu không tạo được ảnh.
    """
    # Khởi tạo client
    client = genai.Client(api_key=google_api_key)

    # Lấy thông tin từ brand_profile
    brand_name = brand_profile.get("brand_name_full", "Thương hiệu")
    logo_style = ", ".join(brand_profile.get("logo_style", [])) or "hiện đại"
    main_color = ", ".join(brand_profile.get("main_color", [])) or "xanh dương"

    # Prompt hướng dẫn AI tạo logo
    prompt = f"""
    Tạo logo cách điệu từ tên thương hiệu "{brand_name}".
    Phong cách: {logo_style}.
    Màu chủ đạo: {main_color}.
    Thiết kế logo dạng vector, nền trong suốt, tinh gọn, sang trọng và chuyên nghiệp.
    """

    try:
        # Gọi API sinh ảnh
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt],
        )

        # Xử lý kết quả trả về
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                print("💬 Mô tả từ model:", part.text)
            elif hasattr(part, "inline_data") and part.inline_data:
                image_data = part.inline_data.data
                image = Image.open(BytesIO(image_data))
                image.save(output_path)
                print(f"✅ Ảnh logo đã được lưu tại: {output_path}")
                return output_path

        print("⚠️ Không có ảnh nào được tạo trong phản hồi.")
        return None

    except Exception as e:
        print("❌ Lỗi khi gọi Gemini API:", e)
        return None
